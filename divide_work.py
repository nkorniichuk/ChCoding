import os
from struct import *
from socket import *

class ETCP():
	def __init__(self, win_size = 256, pack_size = 10):
		self.window_size = win_size
		self.packet_size = pack_size
		self.host = 'localhost'
		self.port = 5000
			
			
	def sendFile(self, filename='testing.txt'):
		fileInfo = os.stat(filename)

		windowsNumber = fileInfo.st_size/(self.window_size*self.packet_size) \
				if fileInfo.st_size%(self.window_size*self.packet_size) == 0 \
				else fileInfo.st_size/(self.window_size*self.packet_size) +1
		
		currentWindow = 0
		curPos = 0
	
		for i in range(windowsNumber):
			
                        curWinSize = self.window_size if i < windowsNumber or \
                                fileInfo.st_size%(self.window_size*self.packet_size) == 0 \
                                else fileInfo.st_size%(self.window_size*self.packet_size)
			
			snd_buffer = self.chunky(filename, curWinSize, curPos)

			print snd_buffer
			print '\n'
# params
	
	def chunky(self, filename, curWinSize, curPos):
                array = []

		with open(filename,'r') as file:
			file.seek(curPos)
			for i in range(CurWinSize):

		                chunk = file.read(self.packet_size)
				if chunk=='':
					break
				elif len(chunk) <= self.packet_size:
					array.append(chunk)
					array[i] = pack('B',i)+array[i]
		#			array[i] = pack('B',(self.curWinSize))+array[i]
			curPos = file.tell()
		return array
	





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

