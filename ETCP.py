#!/usr/bin/python

import os
from struct import *
from pyping import * 
from socket import *
import sys
import time 

''' int: Header codes for different types of acknowledgments
''' 
ACK_BYTE = 200		# first TCP packet header byte
NACK_HEAD_BYTE = 300	# window acknowledgement header byte
FIRST_HEAD_BYTE = 100	# header byte for list with not received data packets
NNACK_HEAD_BYTE = 400	# header byte for list with received data packets

class ETCP():
	'''General class consisting of transmitter and receiver parts
	'''
	def __init__(self, \
				windowSize = 3000, \
				packetSize = 1400, \
				dirChPort = 5000,\
				backChPort = 5001, \
				flowControl = 0.1, \
				destination = '10.33.22.205', \
				debug = True
				):
		''' Constructor method
		Args:
			windowSize (int): specifies initial quantity of data packets in one window
			packetSize (int): initial size of data without headers in one UDP packet
			dirChPort (int): number of the port for communication over UDP socket
			backChPort (int): number of port for communication over TCP socket
			flow (float): initial flow control timeouts value
			destination (str): reciever IP address
			debug (bool): if True activates debug mode with additional errorand info logging 
		'''

		self.windowSize = windowSize
		self.packetSize = packetSize
		self.cursorPosition = 0			# initial cursor position for the file reading

		self.debug = debug

		self.directChannelPort = dirChPort
		self.backChannelPort = backChPort
		
		self.destinationHost = destination

		self.directChannelConnection = ''	# initialize variable for UDP connection for data transmission on both transmitter and reciever sides
		self.backChannelConnection = ''		# initialize variable for TCP connection on transmitter side for file info transmission
		self.backChannelAcceptedConnection = ''	# initialize variable for TCP connection on reciever side for file info reception

		self.transmitterHost = ''		# transmitter IP address 
		self.flowControl = flowControl 		# initialize variable for flow control timer

#################################################################
#								#
#			TRANSMITTER PART			#
#								#
#################################################################

	def sendFile(self, filename):
		''' sendFile  - connection creation on the transmitting side and  
		Args:
			filename (str): name of file intended for sending
		'''
		try:
			fileInfo = os.stat(filename)							# get info about transmitting file
		except:
			if self.debug:
				print 'ERROR::ERROR OCCURED WHILE OPENING A FILE'			# print error log in debug mode
			sys.exit()									# terminate program
		try:
			self.directChannelConnection = socket(AF_INET, SOCK_DGRAM)			# create IPv4 UDP socket for direct transmitter-reciever connection
			self.directChannelConnection.bind(('0.0.0.0', self.directChannelPort))		# bind UDP socket to all available IPv4 addresses
			self.directChannelConnection.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)		# force binding socket to the port to prevent other apps from using selected port

			self.directChannelConnection.setsockopt(SOL_SOCKET, SO_RCVBUF, 327680)		# set the size of receiving buffer for UDP socket
			self.directChannelConnection.setsockopt(SOL_SOCKET, SO_SNDBUF, 327680)		# set the size of sending buffer for UDP socket

			self.backChannelConnection = socket(AF_INET, SOCK_STREAM)			# create IPv4 TCP socket for control data sending during the start of transmission  
			self.backChannelConnection.bind(('0.0.0.0',self.backChannelPort))		# bind TCP socket to all available IPv4 addresses
			self.backChannelConnection.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)		# force binding socket to the port to prevent other apps from using selected port

			self.backChannelConnection.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)		# disable Nagle's algorithm in order to minimize waiting time for TCP packet transmission
			self.backChannelConnection.setsockopt(SOL_SOCKET, SO_SNDBUF, 4194304)		# set the size of sending buffer for TCP socket
			self.backChannelConnection.setsockopt(SOL_SOCKET, SO_RCVBUF, 4194304)		# set the size of receiving buffer for TCP socket

			self.backChannelConnection.connect((self.destinationHost,self.backChannelPort))	# setup TCP connection with the receiver

		except:											# in case of an error
			if self.debug:
				print 'ERROR::ERROR OCCURED WHILE SOCKET ESTABLISHING'			# print error log in debug mode
			self._close()									# close connections
			sys.exit()									# terminate program

		self._firstTCP(filename, fileInfo)							# create and send first TCP packet with info about transmitting file

		windowsNumber = fileInfo.st_size/(self.windowSize*self.packetSize) \			
				if fileInfo.st_size%(self.windowSize*self.packetSize) == 0 \		
				else fileInfo.st_size/(self.windowSize*self.packetSize) +1		# define number of windows that will be transmitted to reciever

		try:
			with open(filename, 'r') as file:													# open transmitting file for reading
				for currentWindow in range(1,windowsNumber+1):											# iterate through the current window

					currentWindowSize = 0													# initial size of current window

					if currentWindow < windowsNumber or fileInfo.st_size%(self.windowSize*self.packetSize) == 0:				# if it is not last window or file size is equal to the integer number of windows
						currentWindowSize = self.windowSize										# set size of current window equal to the initial window size
					else:															# if not
						if fileInfo.st_size%(self.windowSize*self.packetSize)/self.packetSize > 0:					# if file size is greater than the integer number of packets
							if (fileInfo.st_size%(self.windowSize*self.packetSize))%self.packetSize == 0:				# if quantity of packets in last window is integer
								currentWindowSize = (fileInfo.st_size%(self.windowSize*self.packetSize))/self.packetSize	# set current window size equal to quantity of packets
							else:													# if it is not integer
								currentWindowSize = (fileInfo.st_size%(self.windowSize*self.packetSize))/self.packetSize + 1	# set current window size equal to integer quantity of packets
						else:														# if not
							currentWindowSize = 1											# set window size equal to one packet

					window = self._chunky(file, currentWindowSize, currentWindow)								# get data packets for current window
					self._sendWin(window, currentWindowSize, currentWindow)									# send window and resend lost packets
		except:											# in case of error
			if self.debug:
				print 'ERROR::ERROR OCCURED WHILE READING FROM FILE'			# print error log in debug mode

		self.cursorPosition = 0									# reset position of cursor
		self._close()										# close connections

	def _firstTCP(self, filename, fileInfo):
		''' _firstTCP - sending over TCP the first packet to reciever with indormation about file (name, size)
		Args:
			filename (str): name of transmitting file
			fileInfo (sruct): information about transmitting file (size, owner, time of most recent access, etc.)   
		'''
		fileData = filename+':'+str(fileInfo.st_size)					# concatenate name of file with size of file
		message = bytearray([FIRST_HEAD_BYTE,len(fileData)])+fileData			# form initial message by converting heade byte, message length and info about file  
		read = self.backChannelConnection.send(message)					# send formed message to reciever by TCP
		if read == 0:									# if occured error while sending first TCP packet
			if self.debug:
				print 'ERROR::ERROR OCCURED WHILE SENDING FIRST TCP MSG'	# print error log in debug mode	
			self._close()								# close connections
			sys.exit()								# terminate program execution
		else:
			if self.debug:
				print 'INFO::INIT TCP PACKET SENT'				# print log in debug mode 

	def _chunky(self, File, currentWindowSize, currentWindow):
		''' _chunky - reading from file and forming data pieces ready for sending
		Args:
			File: file intended for sending
			currentWindowSize (int): size of the currently transmitting window
			current window (int): index of currently transmitting window
		'''
		array = []									# ininialize empty list for storing packets from current window 
		File.seek(self.cursorPosition)							# look for current cursor position
		for i in range(0, currentWindowSize):						# iterate through current window
			chunk = File.read(self.packetSize)					# read from file amount of bytes that will be send in current packet
			if chunk == '':								# if it is nothing to send
				break								# file is over -> break loop
			elif len(chunk) <= self.packetSize:					# if there are what to send
				array.append(chunk)						# append data to list with packets
				array[i] = pack('>H',i)+pack('>H',currentWindow)+array[i]	# pack headers with packet and window indexes
		self.cursorPosition = File.tell()						# save current position of read pointer
		return array									# return list of packets in current window ready foe sending

	def _sendWin(self, window, currentWindowSize, currentWindow, repeat = []):
		''' _sendWin - performs the sending of packets from current window
		Args:
			window (list): list of packets in current window ready for sending
			currentWindowSize (int): quantity of packets in current window
			currentWindow (int): index of the current window
			repeat (list): list of packets' ids that must be send or resend
		'''
		packetsNumber = repeat if len(repeat) > 0 else range(0,currentWindowSize)		# get list with packets ids that must be send in current window

		for i in packetsNumber:									# iterate through list with ids
			try:
				if len(repeat) > 0:							# if there is what to send
					i = int(i)							# make sure that index is of right type
				self.directChannelConnection.sendto(window[i], (self.destinationHost, self.directChannelPort))		# send packet to reciever 
			except:										# if occured error during the sending
				if self.debug:
					print 'ERROR::ERROR OCCURED WHILE SENDING ', str(i), ' MESSAGE'	# print error log with packet id in debug mode 
				break									# breack sending loop

		if self.debug:
			print 'INFO::WAITING FOR NACK OR ACK'						# print log in debug mode
		nackArray = self._recvNack(currentWindowSize, currentWindow)				# recieve acknowledge with recieved or not recieved packets ids

		if len(nackArray) == 0:									# if list is empty
			if self.debug:
				print 'INFO::ACK RECEIVED'						# print log in debug mode
			return 0									# all window was recieved
		else:											# if list is not empty
			if self.debug:
				print 'INFO::GROUP NACK RECEIVED TRYING TO RESEND...'			# print log in debug mode
			return self._sendWin(window, currentWindowSize, currentWindow, nackArray)	# resend not recieved packets from current window


	def _recvNack(self, currentWindowSize, currentWindow):
		''' _recvNack - recieving and processing acknowledgements due to their types
		Args:
			currentWindowSize (int): size of currently transmitting window
			currentWindow (int): index of the currently transmitting window
		'''
		while 1:
			nackArray = []									# initialize empty list that will contain not recieved packets' ids
			header = self.directChannelConnection.recv(4)					# recieve first 4 bytes
			headByte = unpack('>H',header[0:2])[0]						# unpack header with acknowledgement type
			if headByte == ACK_BYTE:							# if acknowledgement that all packets were recieved
				receivedWindowId = unpack('>H',header[2:4])[0]				# unpack index of recieved window
				if receivedWindowId != currentWindow:					# if index of recieved window is not equal to current window
					continue							# throw this acknowledgement away
				if self.debug:
					print 'INFO::WINDOW RECEIVED'					# print log in debug mode
			elif headByte == NACK_HEAD_BYTE:						# if acknowledgement with not recieved packets was obtained
				if self.debug:
					print 'INFO::NACK RECEIVED'					# print log in debug mode
				data = self.directChannelConnection.recv(65535)				# recieve whole buffer
				nackArray = data[2:].split(',')						# transform string with not recieved packets to list
			elif headByte == NNACK_HEAD_BYTE:						# if acknowledgement with recieved packets was obtained
				if  self.debug:
					print 'INFO::NNACK RECEIVED'					# print log in debug mode
				data = self.directChannelConnection.recv(65535)				# recieve whole buffer
				data = data[2:].split(',')						# transform string with recieved packets to list
				checkArray = [str(item) for item in range(0,currentWindowSize)]		# form list for checking
				nackArray = set(checkArray).difference(set(data))			# compare lists and return list with not recieved packets 
			else:										# if header byte of acknowledgement is unknown
				if self.debug:
					print 'ERROR::UNKNOWN ACK TYPE'					# print log in debug mode
			return nackArray								# return list with ids of packets that must be recended



#################################################################
#								#
#			RECEIVER PART				#
#								#
#################################################################

	def receive(self):
	'''  recieve - connection initialization on reciever side, packets receiving and sending of acknowledgements
	'''
		try:
			self.directChannelConnection = socket(AF_INET,SOCK_DGRAM)					# creating of IPv4 UDP socket for transmitter-reciever connection
			self.directChannelConnection.bind(('0.0.0.0', self.directChannelPort))				# bind UDP socket to all available IPv4 addresses and defined port

			self.directChannelConnection.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)				# force socket binding to disable other apps from using the port
			self.directChannelConnection.setsockopt(SOL_SOCKET, SO_RCVBUF, 327680)				# set the size of the recieving UDP buffer
			self.directChannelConnection.setsockopt(SOL_SOCKET, SO_SNDBUF, 327680)				# set the size of the sending UDP buffer

			self.directChannelConnection.settimeout(0.1)							# set some timeout

			self.backChannelConnection = socket(AF_INET,SOCK_STREAM)					# create TCP socket for file info transmission
			self.backChannelConnection.bind(('0.0.0.0',self.backChannelPort))				# bind TCP socket to all available IPv4 addresses
			self.backChannelConnection.listen(1)								# listening only for one connection in back channel

			self.backChannelConnection.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)				# force binding socket to the port to prevent other apps from using selected port 

			self.backChannelAcceptedConnection , self.transmitterHost = self.backChannelConnection.accept()	# accept TCP connection with transmitter

			self.backChannelAcceptedConnection.setsockopt(SOL_SOCKET, SO_RCVBUF, 4194304)			# set the size of the receiving TCP buffer
			self.backChannelAcceptedConnection.setsockopt(SOL_SOCKET, SO_SNDBUF, 4194304)			# set the size of the sending TCP buffer

			self.backChannelAcceptedConnection.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)			# disable Nagle's algorithm to disable TCP packet waiting

		except:
			if self.debug:
				print 'ERROR::ERROR OCCURED WHILE SOCKET ESTABLISHING'			# print log in debug mode
			self._close()									# close all connections in case of occured error
			sys.exit()									# terminate the program

		headByte = self.backChannelAcceptedConnection.recv(1)					# recieve first header byte of the init message 

		if ord(headByte) == FIRST_HEAD_BYTE:							# if init message was received
			if self.debug:
				print 'INFO::INIT MESSAGE RECEIVED'					# print log in debug mode
		else:											# if it is not header byte of initial message
			if self.debug:
				print 'ERROR::UNKNOWN MESSAGE'						# print log in debug mode
			self._close()									# close all connections
			sys.exit()									# terminate the program

		initMessageDataLength = ord(self.backChannelAcceptedConnection.recv(1))			# recieve 1 byte with current message data length	
		initMessageData = self.backChannelAcceptedConnection.recv(initMessageDataLength)	# recieve all remaining bytes of the initial message 
		initMessageData = initMessageData.split(':')						# transform recieved string to list	
		if self.debug:
			print 'INFO::Filename: ',initMessageData[0],'; Size: ',initMessageData[1]	# print log with file information in debug mode
		if self.debug:
			print 'INFO::STARTING PING...'							# print log in debug mode

		png = ping(self.transmitterHost[0])							# send ICMP ping to transmitter for defining of flow control settings
		self.flowControl = float(png.max_rtt)/1000						# adjust flow control timer according to round-trip time  

		try:
			with open(initMessageData[0],'w+') as File:					# open empty file for writing
				windowsNumber = int(initMessageData[1])/(self.windowSize*self.packetSize) \
					if int(initMessageData[1])%(self.windowSize*self.packetSize) == 0 \
					else int(initMessageData[1])/(self.windowSize*self.packetSize) + 1	# define quantity of windows from init message data, windowSize and packetSize
				for currentWindow in range(1,windowsNumber+1):					# iterate through all windows
					currentWindowSize = 0							# initial window size

					if currentWindow < windowsNumber or int(initMessageData[1])%(self.windowSize*self.packetSize) == 0:	# if it is not last window or transmitted file size is equal to integer number of packets in integer number of windows 
						currentWindowSize = self.windowSize								# size of current window is specified by constructor
					else:													# if not
						if (int(initMessageData[1])%(self.windowSize*self.packetSize))/self.packetSize > 0:		# if file size is greater than number of packets in window
							if (int(initMessageData[1])%(self.windowSize*self.packetSize))%self.packetSize == 0:	# if file size is equal to  integer number of packets
								currentWindowSize = (int(initMessageData[1])%(self.windowSize*self.packetSize))/self.packetSize 	# set current window size equal to left integer number of packets
							else:														# if not
								currentWindowSize = (int(initMessageData[1])%(self.windowSize*self.packetSize))/self.packetSize + 1	# set current window size equal to integer remainning number of packets
						else:
							currentWindowSize = 1		# set current window size equal to one packet

					receiveWindow = [None]*currentWindowSize		# initialize list that will keep in order recieving data packets
					self._recvWin(receiveWindow, File, currentWindow)	# start to recieve packets from current window

		except:										# if error occured
			if self.debug:
				print 'ERROR::ERROR OCCURED WHILE WRITING TO FILE'		# print log in debug mode

		self._close()									# close opened connections


	def _recvWin(self, window, File, currentWindowId, repeat = 0):
		''' _recvWin - performs the receiving of packets from current window
		Args:
			window (list): list of received packets from current window
			File: file where writing of receiving data is performed 
			currentWindowId (int): number of the currently recieving window
			repeat (int): quantity of packets expected to be received 
		'''
		packetsNumber = range(0,repeat) if repeat > 0 else range(0,len(window))		# get quantity of packets in current window
		for i in packetsNumber:								# iterate through current window
			try:
				data  = self.directChannelConnection.recv(4+self.packetSize)	# recieve 4 header bytes and rest data in packet
			except:
				break								# if there is no data in incoming buffer break the cycle to send control information to transmitter 
			packetId = unpack('>H',data[0:2])[0]					# unpack first 2 bytes of header - packet index
			windowId = unpack('>H',data[2:4])[0]					# unpack second 2 bytes of header - index of current window
			if windowId != currentWindowId:						# if packet doesn't belong to current window 
				break								# then break the loop to inform transmitter about packet loss
			window[packetId] = data[4:]						# put recieved data to list in order according to packetId
		nackArray = self._checkWin(window)						# check presence of all packets, choose the type of acknowledgement
		if len(nackArray)>1:								# if not all packets were received
			if self.debug:
				print 'INFO::NOT EVERYTHING RECEIVED CORRECTLY'			# print logs in debug mode
			self._sendNack(nackArray)						# send acknowledgement to transmitter
			if nack[0] == NACK_HEAD_BYTE:						# if list of not recieved packets' ids was send  
				return self._recvWin(window, File, currentWindowId, len(nackArray))	# call itself to receive them
			else:									# if list of recieved packets' ids was send
				return self._recvWin(window, File, currentWindowId, len(window) - len(nackArray))	#call itself to receive the remaining ones
		else:										# if all packets from current window were received
			for i in range(0, len(window)):						# iterate through the window
				File.write(window[i])						# write recieved data to the file
			if self.debug:
				print 'INFO::WINDOW IS RECEIVED AND WRITTEN TO THE FILE'	# print logs in debug mode 
			return self._sendAck(currentWindowId)					# inform transmitter that receiver got all packets from current window

	def _checkWin(self, window):
		'''_checkWin - check recieved packets and decide what kind of acknowledge send to the transmitter to minimize the length of control packet
		Args:
			window (list): list of recieved data packets
		'''
		nackArray = [NACK_HEAD_BYTE]					# initialize list consisting id's of not received data packets
		ackArray = [NNACK_HEAD_BYTE]					# initialize list consisting id's of recieved data packets
		for i in range(0,len(window)):					# iterate through list with recieved packets
			if window[i] == None:					# if item with id i is not present in list of recieved data packets
				nackArray.append(i)				# append data packet id to the end of list with not recieved data packets
			else:							# if item with id i is present in the list of recieved data packets
				ackArray.append(i)				# append data packet id to the end of list with recieved data packets
		if len(ackArray) < len(nackArray) and len(ackArray)!= 1:	# if list of recieved packets is shorter than list of not recieved data packets 
			return ackArray						# choose ackArray for sending
		else:								# if list of not recieved packets is shorter than the list of recieved data packets
			return nackArray					# chose nackArray for sending

	def _sendAck(self, currentWindow):
		''' _sendAck - header packing and sending of window acknowledgement from reciever to transmitter
		Args:
			currentWindow (int): number of currently transmitting window
		'''
		acknowledgeMessage = pack('>H',ACK_BYTE)+pack('>H',currentWindow)							# performing the header packing
		for i in range(0,5):													# repeat sending 5 times to make sure that it will reach destination
			self.directChannelConnection.sendto(acknowledgeMessage, (self.transmitterHost[0],self.directChannelPort))	# sending window acknowledge to transmitter 

	def _sendNack(self, nackArray):
		''' _sendNack - consolidation, header packing and sending of id's list of recieved or not recieved packets 
		Args:
			nackArray (list of ints): array of indexes of recieved or not recieved packets
		'''
		message = str(nackArray[1:])[1:-1]			# concatenate all exept first nackArray items 
		message = message.replace(' ','')			# delete spaces from formed string
		fullNackMessage = pack('>H',nackArray[0])+message	# pack the the zero item of nackArray (NACK or NNACK header byte) and concatinate it with the string
		self.directChannelConnection.sendto(fullNackMessage, (self.transmitterHost[0],self.directChannelPort))		# send formed NACK to the transmitter
		time.sleep(self.flowControl) 				# sleep for amount of time specified by flow controll to give the opportunity for sender to recieve the next NACK 

#################################################################
#								#
#			OTHER METHODS				#
#								#
#################################################################

	def _close(self):
		''' _close - closing of all socket connections that participate in data transmission
		'''
		if self.debug:
			print 'INFO::SOCKET CLEANING STARTED...'
		try:
			self.directChannelConnection.close()			# closing of the direct data channel
			if self.debug:
				print 'INFO::DIRECT CHANNEL CLOSED'		# print log in debug mode
			if self.backChannelAcceptedConnection != '':		# check the status of TCP channel on reciever side
				self.backChannelAcceptedConnection.close()	# closing of this channel
				if self.debug:
					print 'INFO::BACK CHANNEL CLOSED'	# print log in debug mode
			if self.backChannelConnection != '':			# check the status of TCP channel on transmitter side
				self.backChannelConnection.close()		# closing of this channel
				if self.debug:
					print 'INFO::BACK CHANNEL CLOSED'	# print log in debug mode
		except:
			if self.debug:
				print 'ERROR::FAILED TO CLOSE CONNECTIONS'	# print log in debug mode
