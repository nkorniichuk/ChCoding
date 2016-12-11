import os
from struct import *

class ETCP():
	def __init__(self, win_size = 256, pack_size = 10):
		self.window_size = win_size
		self.packet_size = pack_size
		self.host = 'localhost'
		self.port = 5000
			
			
	def send(self, filename='testing.txt'):
		fileInfo = os.stat(filename)
		windowsNumber = fileInfo.st_size/self.window_size \
				if fileInfo.st_size%self.window_size == 0 \
				else fileInfo.st_size/self.window_size +1
		print windowsNumber		
		snd_buffer = []
		
		currentWindow = 0
		curPos = 0
		
		for i in range(windowsNumber):
			self.chunky(filename, fileInfo, \
				currentWindow, windowsNumber, \
				curPos, snd_buffer)
			print snd_buffer
			print '\n'
	
	def chunky(self, \
		filename, \
		fileInfo, \
		currentWindow, \
		windowsNumber, \
		curPos,
		snd_buffer):
		CurWinSize = self.window_size \
			if currentWindow != windowsNumber \
			else fileInfo.st_size % self.window_size
		with open(filename,'r') as file:
			file.seek(curPos)
			for i in range(CurWinSize):
		                chunk = file.read(self.packet_size)
				if chunk=='':
					break
				elif len(chunk) <= self.packet_size:
					snd_buffer.append(chunk)
					snd_buffer[i] = pack('B',i)+snd_buffer[i]
					snd_buffer[i] = pack('B',(self.window_size-1))+snd_buffer[i]
			curPos = file.tell()
		currentWindow += 1
	





#		with open('testing2.txt','w') as fily:
#			for i in range(len(array)):
#				fily.write(array[i])
#
#
#
#
#
#
#def Packing_msg(arr):
#	global num_packet
#	for i in range(len(arr)):
#		if num_packet < window_size:
#			arr[i] = struct.pack('B',num_packet)+arr[i]
#			num_packet += 1
#		else:
#			num_packet = 1
#			arr[i] = struct.pack('B',num_packet)+arr[i]
#			num_packet += 1

