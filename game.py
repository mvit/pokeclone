import pygame #import all of pygame
from pygame.locals import *
from xml.dom.minidom import parse #import xml parser

import settings #load settings
import map #and map manager
import objects #and objects
import font #font manager
import player #class for player
import dialog #class for dialogs
import transition #import all the transitions
import menu #import menu manager

class Game: #class for our game engine
	def __init__(self, g):
		self.g = g #store global variables
		self.surf = pygame.Surface((settings.screen_x, settings.screen_y)) #create a new surface to display on
		self.surf.convert() #convert it to the display format for faster blitting
		self.camera_pos = [368, 336] #set default camera position
		self.objects = {} #list of objects on the map
		self.warps = {} #list of warps on the map
		self.warp_obj = None #warp object
		self.curr_transition = None #current transition object
		self.transition_cb = None #callback when transition completes
		self.obj2pos = {} #dictionary of objects mapped to positions
		self.pos2obj = {} #dictionary of positions mapped to objects
		self.default_dialog = dialog.Dialog(self.g, "standard")
		self.dialog = None
		self.font = self.default_dialog.dlog_font
		self.dialog_drawing = False #set when the dialog is showing text
		self.dialog_result = None #hold result of a dialog
		self.dialog_callback = None #callback for dialog completion
		self.object_data = {} #dictionary of loaded object data
		self.debug = False #whether we're in debug mode or not
		self.menu = menu.Menu(self) #initialize a menu manager
		self.menu_showing = False #whether the menu is being shown
	def start(self):
		self.player = player.Player(self) #initialize a player object
		self.load_map(self.g.save.get_game_prop("game", "curr_map", "data/maps/oasis.tmx")) #load map
		self.map_image = self.map.update() #update it once
		self.transition(transition.FadeIn(32)) #start fade in
	def load_map(self, map_file): #load a map
		self.map = map.Map(self.g, map_file) #load the map
		self.map_file = map_file #save map file
		objects_dom = parse(self.map.properties["object_data"]).documentElement #parse object data file
		self.object_data = {} #clear previous object data
		child = objects_dom.firstChild #get first object data element
		while child is not None: #loop through object data
			if child.localName == "object": #if it's an object element
				self.object_data[child.getAttribute("id")] = child #store it under its id
			child = child.nextSibling #go to next element
	def add_object(self, obj_node): #add an object
		properties = {} #dictionary of the object's properties
		for property in obj_node.getElementsByTagName("property"): #get properties
			properties[property.getAttribute("name")] = property.getAttribute("value") #get a property
		type = obj_node.getAttribute("type") #get type of object
		if type == "Player": #if we're trying to load a player object
			obj = self.player #return it
		else: #otherwise
			obj = objects.obj_types[type](self, obj_node, properties) #load the object
		self.objects[properties["id"]] = obj #store it
		return obj #and return it
	def add_warp(self, pos, obj): #add a warp object
		self.warps[pos] = obj #store the warp
	def prepare_warp(self, pos): #prepare a warp
		self.warp_obj = self.warps[pos] #get the warp object
		#start transition
		self.transition(transition.FadeOut(32), callback=self.perform_warp)
	def perform_warp(self): #actually warp
		warp_obj = self.warp_obj #get the warp object
		#save object data
		for id in self.objects: #loop through all our objects
			self.objects[id].save() #tell them to save
		self.objects = {} #destroy map objects
		self.warps = {}
		self.map = None
		self.warp_obj = False
		self.obj2pos = {}
		self.pos2obj = {}
		self.dialog_drawing = False #we aren't drawing a dialog
		map_file = "data/maps/"+warp_obj["dest_map"] #get destination of warp
		self.load_map(map_file) #load the map
		new_warp = self.objects[warp_obj["dest_warp"]] #get the warp destination
		player = self.objects["player"] #get the player object
		new_pos = new_warp.properties["tile_pos"].split(",") #calculate warp destination
		new_pos = (int(new_pos[0].strip()), int(new_pos[1].strip()))
		player.tile_pos = new_pos #set player position
		player.pos = [((player.tile_pos[0]-1)*16)+8, (player.tile_pos[1]-1)*16]
		player.rect = pygame.Rect(player.pos, player.size)
		self.map_image = self.map.update() #update map once
		self.transition(transition.FadeIn(32)) #start fade back in
	def get_tile_type(self, tile_x, tile_y, player_req=False): #get the type of tile at the given position
		if tile_y < 0 or tile_x < 0: #if the tile is negative
			return -1 #it shouldn't exist
		try: #test if there's an object in the given position
			t = self.pos2obj[(tile_x, tile_y)] #get object
			if t != self.player or not player_req: #if it's not a player or not a player is requesting it
				return -1 #say so
		except: #if there wasn't an object
			pass #don't do anything
		try: #try to get the tile
			return self.map.collision_map.tilemap[tile_y][tile_x]
		except: #if we can't
			return -1 #say so
	def collide(self, tile_pos): #test for a collision
		type = self.get_tile_type(tile_pos[0], tile_pos[1]) #get tile type
		if type != settings.TILE_NORMAL: #if it's not a normal tile
			return True #this is a collison
		return False #otherwise, we're fine
	def set_obj_pos(self, obj, pos): #set an object's position
		pos = tuple(pos[:]) #convert position to tuple
		if obj in self.obj2pos: #if the object has a postion associated with it
			del self.pos2obj[self.obj2pos[obj]] #remove it from the position dict
			del self.obj2pos[obj] #and the object dict
		self.obj2pos[obj] = pos #set object -> position mapping
		self.pos2obj[pos] = obj #set position -> object mapping
	def show_dlog(self, str, talker=None, dlog=None, callback=None): #draw a dialog
		self.dialog_drawing = True #set that we're drawing one
		if dlog is not None: #if a specific dialog has been specified
			self.dialog = dlog #set it
		else: #otherwise, if none was given
			self.dialog = self.default_dialog #use the default one
		self.dialog.draw_text(str) #and tell it to draw
		self.dialog_talking = talker #store who's talking
		self.dialog_callback = callback #store callback
		self.dialog_result = None #clear result
	def interact(self, pos, direction): #interact with an object
		if pos in self.pos2obj: #if this position has an object
			self.pos2obj[pos].interact(direction) #tell the object to interact
	def transition(self, obj, callback=None): #start a transition
		self.curr_transition = obj #store transition object
		self.transition_cb = callback #and callback
	def update(self): #update the engine for this frame
		if self.g.curr_keys[settings.key_debug]: #if the debug key is pressed
			self.debug = not self.debug #invert debug flag
		if self.g.curr_keys[settings.key_menu]: #if the menu key is pressed
			#if no transition is happening and the menu isn't already being shown
			if self.curr_transition is None and self.menu_showing is False and self.dialog_drawing is False:
				self.menu.show() #show menu
				self.menu_showing = True #and mark it as being shown
		#center camera on player
		pos = self.objects["player"].pos #get position of player
		self.camera_pos = (pos[0]-(settings.screen_x/2)+16, pos[1]-(settings.screen_y/2)+16)
		if self.curr_transition is None and self.menu_showing is False: #if there is no transition going on now
			self.map_image = self.map.update() #update the map
			if self.debug: #if we're debugging
				if self.g.curr_keys[settings.key_dbg_save]: #if save key is pressed
					self.save() #do a save
				elif self.g.curr_keys[settings.key_dbg_load]: #if load key is pressed
					self.g.reset() #call game reset function
					return self.surf #and return
		self.surf.fill((0, 0, 0)) #clear surface for black background
		if self.debug: #if we're in debug mode
			for pos in self.pos2obj: #draw object collision tiles
				self.map_image.fill((255, 0, 0), rect=pygame.Rect(((pos[0]*16, pos[1]*16), (16, 16))), special_flags=BLEND_RGB_MULT)
		#draw map
		self.surf.blit(self.map_image, (0, 0), pygame.Rect(self.camera_pos, \
			(settings.screen_x, settings.screen_y))) #blit it
		if self.menu_showing is True: #if the menu is being shown
			self.menu.update(self.surf) #update the menu
		if self.curr_transition is not None: #if there is a transition happening
			r = self.curr_transition.update(self.surf) #update it
			if r: #if it finished
				self.curr_transition = None #destroy transition object
				if self.transition_cb is not None: #if there is a callback
					self.transition_cb() #call it			
					self.transition_cb = None #destroy callback
		if self.dialog_drawing: #if we're drawing a dialog
			result = self.dialog.update(self.surf, (0, 1)) #draw it
			if result is not None: #if we're finished
				self.dialog_drawing = False #stop drawing
				self.dialog_result = result #store result
				if self.dialog_callback: #if there's a callback
					self.dialog_callback(result) #call it with result
				self.dialog_callback = None #clear callback
			elif self.dialog_talking != None: #if somebody is talking
				#draw an arrow to them
				pos = self.dialog_talking.pos
				pos = (pos[0]-self.camera_pos[0]+2, pos[1]-self.camera_pos[1]+10)
				pygame.draw.polygon(self.surf, (161, 161, 161), [[64, 44], [pos[0]+2, pos[1]+2], [82, 44]])
				pygame.draw.polygon(self.surf, (255, 255, 255), [[64, 43], pos, [80, 43]])
		if self.debug: self.font.render(str(self.g.fps), self.surf, (0, 180)) #draw framerate
		return self.surf #return the rendered surface
	def save(self, fname=None): #save our data
		for id in self.objects: #loop through all our objects
			self.objects[id].save() #tell them to save
		if fname is None: #if no save file was specified
			f = settings.save_name #use one in settings
		else: #otherwise
			f = fname #use passed one
		self.g.save.set_game_prop("game", "curr_map", self.map_file) #store map
		self.g.save.save(f) #write out save file