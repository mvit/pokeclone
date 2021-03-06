import pygame #load all of pygame
from pygame.locals import *

import settings #load settings
import animation #load animation manager
import script #load script manager

#utility functions
def get_direction_name(direction): #return a name for each direction
	if direction == 0:
		return "up"
	elif direction == 1:
		return "down"
	elif direction == 2:
		return "left"
	elif direction == 3:
		return "right"
		
def get_direction_num(direction): #return a number for each direction name
	if direction == "up":
		return 0
	elif direction == "down":
		return 1
	elif direction == "left":
		return 2
	elif direction == "right":
		return 3

#class to manage object movement
class MovementManager:
	def __init__(self, obj): #initialize the manager
		self.obj = obj #store object
		self.curr_movement = [] #current movement directions
		self.store_movement = [] #stored movement directions, used for resuming
		self.move_list = [] #list of movements
		self.running = False #whether we're currently supposed to be auto moving
		self.repeat = False #whether we are going to repeat the movement list
		self.move_index = 0 #current movement index
		self.resume = False #whether we're going to resume the movement list
		self.moving = False #whether we're moving at all
	def load_move_dom(self, dom): #load a movement list from xml
		move_list = [] #list of movements
		child = dom.firstChild #get first movement
		default_speed = int(dom.getAttribute("speed")) #get default speed
		while child is not None: #loop through movement list
			if child.localName == "move": #if it's a movement command
				#get movement speed
				speed = int(child.getAttribute("speed")) if child.getAttribute("speed") != "" else default_speed
				dist = int(child.getAttribute("dist")) #get movement distance
				dir = get_direction_num(child.getAttribute("dir")) #get direction
				move_list.append([dir, dist, speed]) #add it to movement list
			elif child.localName == "wait": #if it's a wait command
				frames = int(child.getAttribute("frames")) #get number of frames to wait
				dir = get_direction_num(child.getAttribute("dir")) #get direction
				move_list.append([dir, frames, -1]) #add it to movement list
			child = child.nextSibling #go to next movement command
		self.load_move_list(move_list) #set movement list we generated
	def load_move_list(self, move_list, repeat=True): #load a movement list
		self.running = True #we're running now
		self.repeat = repeat #set repeat
		self.move_list = move_list #set movement list
		self.move_index = -1 #set move index to starting
		self.resume = False #clear other variables
		self.moving = True
		self._next_movement() #go to next movement command
	def _next_movement(self): #go to next movement
		self.move_index += 1 #increment move index
		if self.move_index == len(self.move_list): #if we're at the end of the movement list
			if self.repeat: #if we're supposed to repeat
				self.move_index = 0 #zero movement index
			else: #if we're not supposed to repeat
				self.moving = False #stop doing things
				self.running = False
				self.obj.animator.set_animation("stand_"+get_direction_name(self.move_list[-1][0])) #set stand animation
				return
		self.curr_movement = self.move_list[self.move_index][:] #load move list
		self._start_move() #start moving
	def _start_move(self): #start movement
		dir, dist, speed = self.curr_movement #load current movement
		self.moving = True #start moving
		#calculate movement deltas
		if dir == 0: #moving up
			delta = (0, -speed)
		elif dir == 1: #down
			delta = (0, speed)
		elif dir == 2: #left
			delta = (-speed, 0)
		elif dir == 3: #right
			delta = (speed, 0)
		#set movement animation
		if speed < 0: #if it's just a wait command
			self.obj.animator.set_animation("stand_"+get_direction_name(dir)) #set stand animation
		else: #otherwise, 
			self.obj.animator.set_animation("walk_"+get_direction_name(dir)) #set walk animation
		self.pix_pos = 0 #number of pixels we've moved within the tile
		self.delta = delta #store delta
		self.check_collide = False
		if speed > 0: #if we're not doing a wait command
			#calculate new tile position
			if dir == 0:
				self.obj.tile_pos[1] -= 1
			elif dir == 1:
				self.obj.tile_pos[1] += 1
			elif dir == 2:
				self.obj.tile_pos[0] -= 1
			elif dir == 3:
				self.obj.tile_pos[0] += 1
			#if we're going to collide with something
			if self.obj.game.collide(self.obj.tile_pos):
				self.check_collide = True #mark that we need to check it
			else: #if we can move fine
				self.obj.game.set_obj_pos(self.obj, self.obj.tile_pos) #set object position
	def move_to(self, dir, dist, speed, resume=True): #set a movement
		self.resume = resume #set whether we're supposed to resume or not
		self.store_movement = self.curr_movement[:] #back up movement
		self.store_delta = self.delta #and delta
		self.store_pix_pos = self.pix_pos #and pixel position
		self.curr_movement = [dir, dist, speed] #store current movement
		self.running = False #we're not supposed to be automatically moving any more
		self._start_move() #start moving
	def update(self): #update movement
		if not self.moving: #if we're not doing anything
			return #don't do anything
		dir, dist, speed = self.curr_movement #load current movement
		if speed < 0: #if this is a wait command
			self.curr_movement[1] -= 1 #decrement a frame
			if self.curr_movement[1] == 0: #if we're finished waiting
				self._next_movement() #go to next move command
			return #don't do anything else
		if self.check_collide: #if we need to check for collisions
			if not self.obj.game.collide(self.obj.tile_pos): #if we can move into our tile
				self.check_collide = False
				self.obj.game.set_obj_pos(self.obj, self.obj.tile_pos) #set object position
		if not self.check_collide and self.curr_movement[1] > 0: #if we can collide fine
			self.obj.pos[0] += self.delta[0] #move object according to speed
			self.obj.pos[1] += self.delta[1]
			self.pix_pos += speed #add speed to pixel position
		if self.pix_pos > 15: #if we've gone a whole tile
			self.curr_movement[1] -= 1 #remove one from distance
			self.pix_pos -= 16 #remove a tile's worth of pixels
			#calculate new tile position
			if dir == 0:
				self.obj.tile_pos[1] -= 1
			elif dir == 1:
				self.obj.tile_pos[1] += 1
			elif dir == 2:
				self.obj.tile_pos[0] -= 1
			elif dir == 3:
				self.obj.tile_pos[0] += 1
			#if we're going to collide with something
			if self.obj.game.collide(self.obj.tile_pos):
				self.check_collide = True #mark that we need to check it
			else: #if we can move fine
				self.obj.game.set_obj_pos(self.obj, self.obj.tile_pos) #set object position
		if self.curr_movement[1] == 0 and self.check_collide == False: #if we're finished moving
			#un-calculate tile position
			if dir == 0:
				self.obj.tile_pos[1] += 1
			elif dir == 1:
				self.obj.tile_pos[1] -= 1
			elif dir == 2:
				self.obj.tile_pos[0] += 1
			elif dir == 3:
				self.obj.tile_pos[0] -= 1
			#snap object's position to tile
			self.obj.pos = [((self.obj.tile_pos[0]-1)*16)+8, (self.obj.tile_pos[1]-1)*16]
			self.obj.game.set_obj_pos(self.obj, self.obj.tile_pos) #set object position
			if self.running: #if we're supposed to be automatically running
				self._next_movement() #go to the next movement
			elif self.resume: #otherwise, if we're supposed to resume auto movement
				self.running = True #start auto movement
				self.resume = False #stop worrying about resuming
				self.curr_movement = self.store_movement[:] #restore backed up stuff
				self.delta = self.store_delta
				self.pix_pos = self.store_pix_pos

#class that handles rendering generic objects, pretty much
#the same as a pygame sprite
class RenderedObject:
	def __init__(self): #have init defined for consistency
		pass #but it doesn't need to do anything
	def draw(self, surf): #draw ourselves onto a surface
		surf.blit(self.image, self.rect.topleft) #perform the blit
	def save(self):
		pass #we don't need to save anything
		
#class that renders NPCs, automatically draws shadow
class RenderedNPC(RenderedObject):
	def __init__(self):
		RenderedObject.__init__(self) #init parent class
		self.shadow = pygame.image.load("data/objects/npcshadow.png") #load shadow image
		self.shadow.convert_alpha() #convert the image for faster drawing
	def draw(self, surf): #draw ourselves onto a given surface
		surf.blit(self.shadow, (self.rect.x+8, self.rect.y+25)) #draw shadow
		RenderedObject.draw(self, surf) #call renderer for parent class

#warp point object
class Warp:
	def __init__(self, game, element, properties):
		self.g = game.g #store parameters
		self.game = game
		self.properties = properties
		#get tile we're monitoring
		t = self.properties["tile_pos"].split(",")
		self.tile_x = int(t[0].strip())
		self.tile_y = int(t[1].strip())
		game.add_warp((self.tile_x, self.tile_y), self.properties) #add the warp
		self.visible = False #we're not rendering anything
	def interact(self, pos):
		pass #don't interact
	def update(self): #we don't need to do any updates
		pass
	def save(self): #we don't need to save anything
		pass

#sign object
class Sign:
	def __init__(self, game, element, properties):
		self.game = game #store parameters
		self.text = properties["text"] #store text to show
		#get our tile position
		t = properties["tile_pos"].split(",")
		self.tile_pos = (int(t[0].strip()), int(t[1].strip())) #store position
		game.set_obj_pos(self, self.tile_pos) #set our position
		self.visible = False #we're not rendering anything
	def interact(self, pos): #handle the player interacting with us
		self.game.show_dlog(self.text) #show our text
	def update(self):
		pass #we don't need to do any updates
	def save(self): #we don't need to save anything
		pass
		
#generic NPC
class NPC(RenderedNPC):
	def __init__(self, game, element, properties):
		RenderedNPC.__init__(self) #init the renderer class
		self.properties = properties #store parameters
		self.game = game
		t = properties["tile_pos"].split(",") #load tile position
		self.tile_pos = [int(t[0].strip()), int(t[1].strip())]
		self.pos = [((self.tile_pos[0]-1)*16), (self.tile_pos[1]-1)*16] #set real position
		self.image = None #we have no image for now
		self.inited = False #mark that we haven't been initialized fully yet
		self.interacting = False #mark that we're not interacting
		self.visible = True #and we should be showing ourselves
	def do_init(self): #perform initialization on first update
		self.inited = True #we've initialized now
		properties = self.properties #load properties
		game = self.game #and game object
		self.obj_data = game.object_data[properties["id"]] #get our associated data
		#load an animator
		self.animator = animation.AnimationGroup(game.g, self, self.obj_data.getElementsByTagName("anim")[0].getAttribute("file"))
		self.animator.set_animation("stand_down") #set animation
		self.animator.update() #update animation once
		#and a movement manager
		self.move_manager = MovementManager(self)
		#load movement list
		self.move_manager.load_move_dom(self.obj_data.getElementsByTagName("movement")[0])
		self.script_manager = script.Script(self) #initialize script manager
		self.interaction_script = self.obj_data.getElementsByTagName("script")[0] #load script
	def interact(self, pos):
		#make ourselves face to who's talking
		new_pos = [1, 0, 3, 2][pos]
		self.stored_anim = self.animator.curr_animation #store current animation
		self.animator.set_animation("stand_"+get_direction_name(new_pos)) #set standing one
		self.interacting = True #we're currently interacting
		self.script_manager.start_script(self.interaction_script) #start interaction script
	def update(self):
		if not self.inited: self.do_init() #intialize if we haven't already
		if not self.interacting: #if we aren't interacting
			if self.game.dialog_drawing: return #return if a dialog is being drawn
			self.move_manager.update() #update our movement
			self.rect = pygame.Rect(self.pos, (32, 32)) #update sprite rect
		else: #if we are
			self.script_manager.update() #update script
			self.interacting = self.script_manager.running #set whether we're interacting
			if not self.interacting: #if we've stopped needing to
				self.animator.curr_animation = self.stored_anim #restore stored animation
		self.animator.update() #and our animation
		
#dictionary to hold which classes go with which objects
obj_types = {"warp": Warp, #warp object \
"sign":Sign, #a sign object\
"npc":NPC} #an NPC