import os

num_packet = 1
window_size = 256
packet_size = 10
p = 0
filename = 'testing.txt'
size = 0
windows = 0

def _first():
	global size = os.state(file)
	global windows
	if size%window_size > 0:
		windows = size/window_size+1
	else 
		windows = size/window_size

def Chunky():
	with open(filename,'r') as file:
	       	f = os.stat(file)
		if f.st_size%255==0:
			window_number = f.st_size/255
		else:
			window_number = f.st_size/255
			last_window_size = f.st_size%255
		array = []
		global p
		file.seek(p)
		for i in range(window_size):
	                chunk = file.read(packet_size)
			if chunk=='' or len(chunk)!= packet_size:
				break
			else:
				array.append(chunk)
				array[i] = struct.pack('B',i)+array[i]
				array[i] = struct.pack('B',(window_size-1))+array[i]
		p = file.tell()






		with open('testing2.txt','w') as fily:
			for i in range(len(array)):
				fily.write(array[i])






def Packing_msg(arr):
	global num_packet
	for i in range(len(arr)):
		if num_packet < window_size:
			arr[i] = struct.pack('B',num_packet)+arr[i]
			num_packet += 1
		else:
			num_packet = 1
			arr[i] = struct.pack('B',num_packet)+arr[i]
			num_packet += 1

