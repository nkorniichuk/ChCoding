import os
from struct import *
from pyping import * 
from socket import *
import sys
import time 

ACK_BYTE = 200
NACK_HEAD_BYTE = 300
FIRST_HEAD_BYTE = 100
NNACK_HEAD_BYTE = 400

class ETCP():
	def __init__(self, \
				windowSize = 3000, \
				packetSize = 1400, \
				dirChPort = 5000,\
				backChPort = 5001, \
				flow = 0.1, \
				destination = '10.33.22.205', \
				debug = True
				):

		self.windowSize = windowSize
		self.packetSize = packetSize
		self.cursorPosition = 0

		self.debug = debug

		self.directChannelPort = dirChPort
		self.backChannelPort = backChPort
		
		self.destinationHost = destination

		self.directChannelConnection = ''
		self.backChannelConnection = ''
		self.backChannelAcceptedConnection = ''

		self.transmitterHost = ''
		self.flowControll = flow

#############################################################
#															#
#					TRANSMITTER PART						#
#															#
#############################################################

	def sendFile(self, filename):
		try:
			fileInfo = os.stat(filename)
		except:
			if self.debug:
				print 'ERROR::ERROR OCCURED WHILE OPENING A FILE'
			sys.exit()
		try:
			self.directChannelConnection = socket(AF_INET, SOCK_DGRAM)
			self.directChannelConnection.bind(('0.0.0.0', self.directChannelPort))
			self.directChannelConnection.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

			self.directChannelConnection.setsockopt(SOL_SOCKET, SO_RCVBUF, 327680)
			self.directChannelConnection.setsockopt(SOL_SOCKET, SO_SNDBUF, 327680)

			self.backChannelConnection = socket(AF_INET, SOCK_STREAM)
			self.backChannelConnection.bind(('0.0.0.0',self.backChannelPort))
			self.backChannelConnection.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

			self.backChannelConnection.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
			self.backChannelConnection.setsockopt(SOL_SOCKET, SO_SNDBUF, 4194304)
			self.backChannelConnection.setsockopt(SOL_SOCKET, SO_RCVBUF, 4194304)

			self.backChannelConnection.connect((self.destinationHost,self.backChannelPort))

		except:
			if self.debug:
				print 'ERROR::ERROR OCCURED WHILE SOCKET ESTABLISHING'
			self._close()
			sys.exit()

		self._firstTCP(filename, fileInfo)

		windowsNumber = fileInfo.st_size/(self.windowSize*self.packetSize) \
				if fileInfo.st_size%(self.windowSize*self.packetSize) == 0 \
				else fileInfo.st_size/(self.windowSize*self.packetSize) +1

		try:
			with open(filename, 'r') as file:
				for currentWindow in range(1,windowsNumber+1):

					currentWindowSize = 0

					if currentWindow < windowsNumber or fileInfo.st_size%(self.windowSize*self.packetSize) == 0:
						currentWindowSize = self.windowSize
					else:
						if fileInfo.st_size%(self.windowSize*self.packetSize)/self.packetSize > 0:
							if (fileInfo.st_size%(self.windowSize*self.packetSize))%self.packetSize == 0:
								currentWindowSize = (fileInfo.st_size%(self.windowSize*self.packetSize))/self.packetSize
							else:
								currentWindowSize = (fileInfo.st_size%(self.windowSize*self.packetSize))/self.packetSize + 1
						else:
							currentWindowSize = 1

					window = self._chunky(file, currentWindowSize, currentWindow)
					self._sendWin(window, currentWindowSize, currentWindow)
		except:
			if self.debug:
				print 'ERROR::ERROR OCCURED WHILE WRITING TO FILE'

		self.cursorPosition = 0
		self._close()

	def _firstTCP(self, filename, fileInfo):
		fileData = filename+':'+str(fileInfo.st_size)
		message = bytearray([FIRST_HEAD_BYTE,len(fileData)])+fileData
		read = self.backChannelConnection.send(message)
		if read == 0:
			if self.debug:
				print 'ERROR::ERROR OCCURED WHILE SENDING FIRST TCP MSG'
			self._close()
			sys.exit()
		else:
			if self.debug:
				print 'INFO::INIT TCP PACKET SENT'

	def _chunky(self, File, currentWindowSize, currentWindow):
		array = []
		File.seek(self.cursorPosition)
		for i in range(0, currentWindowSize):
			chunk = File.read(self.packetSize)
			if chunk == '':
				break
			elif len(chunk) <= self.packetSize:
				array.append(chunk)
				array[i] = pack('>H',i)+pack('>H',currentWindow)+array[i]
		self.cursorPosition = File.tell()
		return array

	def _sendWin(self, window, currentWindowSize, currentWindow, repeat = []):
		packetsNumber = repeat if len(repeat) > 0 else range(0,currentWindowSize)

		for i in packetsNumber:
			try:
				if len(repeat) > 0:
					i = int(i)
				self.directChannelConnection.sendto(window[i], (self.destinationHost, self.directChannelPort))
			except:
				if self.debug:
					print 'ERROR::ERROR OCCURED WHILE SENDING ', str(i), ' MESSAGE'
				break

		if self.debug:
			print 'INFO::WAITING FOR NACK OR ACK'
		nackArray = self._recvNack(currentWindowSize, currentWindow)

		if len(nackArray) == 0:
			if self.debug:
				print 'INFO::ACK RECEIVED'
			return 0
		else:
			if self.debug:
				print 'INFO::GROUP NACK RECEIVED TRYING TO RESEND...'
			return self._sendWin(window, currentWindowSize, currentWindow, nackArray)


	def _recvNack(self, currentWindowSize, currentWindow):
		while 1:
			nackArray = []
			header = self.directChannelConnection.recv(4)
			headByte = unpack('>H',header[0:2])[0]
			if headByte == ACK_BYTE:
				receivedWindowId = unpack('>H',header[2:4])[0]
				if receivedWindowId != currentWindow:
					continue
				if self.debug:
					print 'INFO::WINDOW RECEIVED'
			elif headByte == NACK_HEAD_BYTE:
				if self.debug:
					print 'INFO::NACK RECEIVED'
				data = self.directChannelConnection.recv(65535)
				nackArray = data[2:].split(',')
			elif headByte == NNACK_HEAD_BYTE:
				if  self.debug:
					print 'INFO::NNACK RECEIVED'
				data = self.directChannelConnection.recv(65535)
				data = data[2:].split(',')
				checkArray = [str(item) for item in range(0,currentWindowSize)]
				nackArray = set(checkArray).difference(set(data))
			else:
				if self.debug:
					print 'ERROR::UNKNOWN ACK TYPE'
			return nackArray



#############################################################
#															#
#						RECEIVER PART						#
#															#
#############################################################

	def receive(self):
		try:
			self.directChannelConnection = socket(AF_INET,SOCK_DGRAM)
			self.directChannelConnection.bind(('0.0.0.0', self.directChannelPort))

			self.directChannelConnection.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
			self.directChannelConnection.setsockopt(SOL_SOCKET, SO_RCVBUF, 327680)
			self.directChannelConnection.setsockopt(SOL_SOCKET, SO_SNDBUF, 327680)

			self.directChannelConnection.settimeout(0.1)

			self.backChannelConnection = socket(AF_INET,SOCK_STREAM)
			self.backChannelConnection.bind(('0.0.0.0',self.backChannelPort))
			self.backChannelConnection.listen(1)

			self.backChannelConnection.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

			self.backChannelAcceptedConnection , self.transmitterHost = self.backChannelConnection.accept()
			
			self.backChannelAcceptedConnection.setsockopt(SOL_SOCKET, SO_RCVBUF, 4194304)
			self.backChannelAcceptedConnection.setsockopt(SOL_SOCKET, SO_SNDBUF, 4194304)

			self.backChannelAcceptedConnection.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)

		except:
			if self.debug:
				print 'ERROR::ERROR OCCURED WHILE SOCKET ESTABLISHING'
			self._close()
			sys.exit()

		headByte = self.backChannelAcceptedConnection.recv(1)

		if ord(headByte) == FIRST_HEAD_BYTE:
			if self.debug:
				print 'INFO::INIT MESSAGE RECEIVED'
		else:
			if self.debug:
				print 'ERROR::UNKNOWN MESSAGE'
			self._close()
			sys.exit()

		initMessageDataLength = ord(self.backChannelAcceptedConnection.recv(1))
		initMessageData = self.backChannelAcceptedConnection.recv(initMessageDataLength)
		initMessageData = initMessageData.split(':')
		if self.debug:
			print 'INFO::Filename: ',initMessageData[0],'; Size: ',initMessageData[1]
		if self.debug:
			print 'INFO::STARTING PING...'

		png = ping(self.transmitterHost[0])
		self.flowControll = float(png.max_rtt)/1000

		try:
			with open(initMessageData[0],'w+') as File:
				windowsNumber = int(initMessageData[1])/(self.windowSize*self.packetSize) \
					if int(initMessageData[1])%(self.windowSize*self.packetSize) == 0 \
					else int(initMessageData[1])/(self.windowSize*self.packetSize) + 1
				for currentWindow in range(1,windowsNumber+1):
					currentWindowSize = 0

					if currentWindow < windowsNumber or int(initMessageData[1])%(self.windowSize*self.packetSize) == 0:
						currentWindowSize = self.windowSize
					else:
						if (int(initMessageData[1])%(self.windowSize*self.packetSize))/self.packetSize > 0:
							if (int(initMessageData[1])%(self.windowSize*self.packetSize))%self.packetSize == 0:
								currentWindowSize = (int(initMessageData[1])%(self.windowSize*self.packetSize))/self.packetSize
							else:
								currentWindowSize = (int(initMessageData[1])%(self.windowSize*self.packetSize))/self.packetSize + 1
						else:
							currentWindowSize = 1

					receiveWindow = [None]*currentWindowSize
					self._recvWin(receiveWindow, File, currentWindow)

		except:
			if self.debug:
				print 'ERROR::ERROR OCCURED WHILE WRITING TO FILE'

		self._close()


	def _recvWin(self, window, File, currentWindowId, repeat = 0):
		packetsNumber = range(0,repeat) if repeat > 0 else range(0,len(window))
		for i in packetsNumber:
			try:
				data  = self.directChannelConnection.recv(4+self.packetSize)
			except:
				break
			packetId = unpack('>H',data[0:2])[0]
			windowId = unpack('>H',data[2:4])[0]
			if windowId != currentWindowId:
#				time.sleep(0.01)	!!!don't remember if we need this!!!
				break
			window[packetId] = data[4:]
		nackArray = self._checkWin(window)
		if len(nackArray)>1:
			if self.debug:
				print 'INFO::NOT EVERYTHING RECEIVED CORRECTLY'
			self._sendNack(nackArray)
			if nack[0] == NACK_HEAD_BYTE:
				return self._recvWin(window, File, currentWindowId, len(nackArray))
			else:
				return self._recvWin(window, File, currentWindowId, len(window) - len(nackArray))
		else:
			for i in range(0, len(window)):
				File.write(window[i])
			if self.debug:
				print 'INFO::WINDOW IS RECEIVED AND WRITTEN TO THE FILE'
			return self._sendAck(currentWindowId)

	def _checkWin(self, window):
		nackArray = [NACK_HEAD_BYTE]
		ackArray = [NNACK_HEAD_BYTE]
		for i in range(0,len(window)):
			if window[i] == None:
				nackArray.append(i)
			else:
				ackArray.append(i)
		if len(ackArray) < len(nackArray) and len(ackArray)!= 1:
			return ackArray
		else:
			return nackArray

	def _sendAck(self, currentWindow):
		acknowledgeMessage = pack('>H',ACK_BYTE)+pack('>H',currentWindow)
		for i in range(0,5):
			self.directChannelConnection.sendto(acknowledgeMessage, (self.transmitterHost[0],self.directChannelPort))

	def _sendNack(self, nackArray):
		message = str(nackArray[1:])[1:-1]
		message = message.replace(' ','')
		fullNackMessage = pack('>H',nackArray[0])+message
		self.directChannelConnection.sendto(fullNackMessage, (self.transmitterHost[0],self.directChannelPort))
		time.sleep(self.flowControll)

#############################################################
#															#
#						OTHER METHODS						#
#															#
#############################################################

	def _close(self):
		if self.debug:
			print 'INFO::SOCKET CLEANING STARTED...'
		try:
			self.directChannelConnection.close()
			if self.debug:
				print 'INFO::DIRECT CHANNEL CLOSED'
			if self.backChannelAcceptedConnection != '':
				self.backChannelAcceptedConnection.close()
				if self.debug:
					print 'INFO::BACK CHANNEL CLOSED'
			if self.backChannelConnection != '':
				self.backChannelConnection.close()
				if self.debug:
					print 'INFO::BACK CHANNEL CLOSED'
		except:
			pass