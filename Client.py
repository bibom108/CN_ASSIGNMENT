from cmath import inf
from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os

import time    

#Run: init, create, connect server, listen RPT, send request and receive data socket, write frame
from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	DESCRIBE = 4
	FORWARD = 5
	BACKWARD = 6
	
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		self.expFrameNbr = 0
		self.statPacketsLost = 0
		self.statTotalBytes = 0
		self.statTotalPlayTime = 0
		self.startTime = 0
		self.totalFrames = 0  
	# Initiatio	
	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		# self.setup = Button(self.master, width=16, padx=3, pady=3)
		# self.setup["text"] = "Setup"
		# self.setup["command"] = self.setupMovie
		# self.setup.grid(row=1, column=0, padx=2, pady=2)
		self.master.geometry("680x520")
		self.iplay = PhotoImage(file="./image/play.png").zoom(3).subsample(51)
		self.ipause = PhotoImage(file="./image/pause.png").zoom(3).subsample(51)
		self.istop = PhotoImage(file="./image/stop-button.png").zoom(3).subsample(51)
		self.ifor = PhotoImage(file="./image/fast-forward.png").zoom(3).subsample(51)
		self.iback = PhotoImage(file="./image/rewind.png").zoom(3).subsample(51)
		self.ides = PhotoImage(file="./image/search.png").zoom(3).subsample(51)

		
		# Create Play button		
		self.start = Button(self.master, padx=3, pady=3, width=100, image=self.iplay)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=0, padx=2, pady=2, sticky=W+E+N+S)
		
		# Create Pause button			
		self.pause = Button(self.master, padx=3, pady=3, width=100, image=self.ipause)
		# self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=1, padx=2, pady=2, sticky=W+E+N+S)
		
		# Create Teardown button
		self.teardown = Button(self.master, padx=3, pady=3, width=100, image=self.istop)
		# self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=2, padx=2, pady=2, sticky=W+E+N+S)

		self.describe = Button(self.master, padx=3, pady=3, width=100, image=self.ides)
		# self.describe["text"] = "Describe"
		self.describe["command"] =  self.describeSession
		self.describe.grid(row=1, column=3, padx=2, pady=2, sticky=W+E+N+S)

		self.describe = Button(self.master, padx=3, pady=3, width=100, image=self.iback)
		# self.describe["text"] = "Backward"
		self.describe["command"] =  self.backWardSession
		self.describe.grid(row=1, column=4, padx=2, pady=2, sticky=W+E+N+S)

		self.describe = Button(self.master, padx=3, pady=3, width=100, image=self.ifor)
		# self.describe["text"] = "Forward"
		self.describe["command"] =  self.forwardSession
		self.describe.grid(row=1, column=5, padx=2, pady=2, sticky=W+E+N+S)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=6, sticky=W+E+N+S, padx=5, pady=5)
		self.displays = []
		for i in range(6):
			DLabel = Label(self.master, height=1)
			DLabel.grid(row=2 + i, column=0, columnspan=6,sticky=W,padx=5, pady=5)
			self.displays.append(DLabel)
	
	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)
	
	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN)		
		self.master.destroy() # Close the gui window
		try:
			os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video

		except:
			print("Can't delete cache.")

	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
	
	def playMovie(self):
		"""Play button handler."""
		if self.state == self.INIT:
			self.setupEvent = threading.Event()
			self.sendRtspRequest(self.SETUP)
			self.setupEvent.wait(timeout=0.5)

		if self.state == self.READY:
			# Create a new thread to listen for RTP packets
			threading.Thread(target=self.listenRtp).start()
			self.playEvent = threading.Event()
			self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)
	
	def describeSession(self):
		"""Describe button handler."""
		self.sendRtspRequest(self.DESCRIBE)

	def backWardSession(self):
		"""Forward button handler."""
		self.sendRtspRequest(self.BACKWARD)

	def forwardSession(self):
		"""Forward button handler."""
		self.sendRtspRequest(self.FORWARD)
	def listenRtp(self):		
		"""Listen for RTP packets."""
		while True:
			try:
				data = self.rtpSocket.recv(20480)
				# this is packet recieve. 20480 is buffer size
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
				
					# make the packet receive has the class type of Packet
					self.expFrameNbr += 1 
						
					currFrameNbr = rtpPacket.seqNum()
					print("Current Seq Num: " + str(currFrameNbr))
											
					if currFrameNbr > self.frameNbr: # Discard the late packet
						self.frameNbr = currFrameNbr
						payload = rtpPacket.getPayload()
						self.updateMovie(self.writeFrame(payload))
						#this packet cop to cache
						#ready to fast present
					
					self.totalFrames += 1
					
					# Compare expected frame number and gotten frame number
					if self.expFrameNbr != currFrameNbr: 
						self.statPacketsLost += 1
						
					# Calculate total data received 
					payload_length = len(payload)
					self.statTotalBytes += payload_length
						
					# Calculate total play time of the session
					curTime = time.time()
					self.statTotalPlayTime += curTime - self.startTime
					self.operationTime = curTime - self.startTime
					self.startTime = curTime

					# Display the statistics about the session
					self.displays[0]["text"] = 'Current frame: ' + str(currFrameNbr)
					self.displays[1]["text"] = 'Frame per second (fps): ' + str(format(1/self.operationTime,".2f")) 
					self.displays[2]["text"] = 'Data received: ' + str(self.statTotalBytes) + ' bytes'
					self.displays[3]["text"] = 'Data Rate: ' + str(format(payload_length / self.operationTime,".2f")) + ' bytes/s'
					self.displays[4]["text"] = 'Packets Lost: '   + str(self.statPacketsLost) + ' packets'
					self.displays[5]["text"] = 'Packets Lost Rate: ' + str(float(self.statPacketsLost / currFrameNbr)) 	

			except:
			# Stop listening upon requesting PAUSE or TEARDOWN
				if self.playEvent.isSet(): 
					break
			
			# Upon receiving ACK for TEARDOWN request,
			# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break	
	
					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		file = open(cachename, "wb")
		file.write(data)
		file.close()
		
		return cachename
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		photo = ImageTk.PhotoImage(Image.open(imageFile))
		self.label.configure(image = photo, height=288) 
		self.label.image = photo
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#https://www.youtube.com/watch?v=7-O7yeO3hNQ
		#this is client socket in youtube

		try:#this is ip and port for connect, input a tuple
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			tkinter.messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		#-------------
		# TO COMPLETE
		#-------------
		#TODO TOUNDERSTAND
		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			threading.Thread(target=self.recvRtspReply).start()
			# Update RTSP sequence number.
			self.rtspSeq += 1

			# Write the RTSP request to be sent.
			request = 'SETUP ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nTransport: RTP/UDP; client_port= ' + str(self.rtpPort)

			# Keep track of the sent request.
			self.requestSent = self.SETUP

		# Play request
		#save the request so the server can access and know what to do
		elif requestCode == self.PLAY and self.state == self.READY:
			self.rtspSeq += 1
			request = 'PLAY ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)
			self.requestSent = self.PLAY

		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			self.rtspSeq += 1
			request = 'PAUSE ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)
			self.requestSent = self.PAUSE

		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			self.rtspSeq += 1
			request = 'TEARDOWN ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)
			self.requestSent = self.TEARDOWN
		
		# Describe request	
		elif requestCode == self.DESCRIBE:
			self.rtspSeq += 1
			request = 'DESCRIBE ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)
			self.requestSent = self.DESCRIBE

		elif requestCode == self.FORWARD:
			self.rtspSeq += 1
			request = 'FORWARD ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)
			self.requestSent = self.FORWARD

		elif requestCode == self.BACKWARD:
			self.rtspSeq += 1
			request = 'BACKWARD ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)
			self.requestSent = self.BACKWARD
		else:
			return

		# Send the RTSP request using rtspSocket.
		# self.rtspSocket.send(request.)
		self.rtspSocket.send(request.encode('utf-8'))

		print('\nData sent:\n' + request)
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			reply = self.rtspSocket.recv(1024)
			
			if reply: #RTSPSOCKET keep adding the new data
				self.parseRtspReply(reply.decode("utf-8"))

			# Close the RTSP socket upon requesting Teardown
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break
	
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		lines = data.split('\n')

		if 'Description' in lines[1]:
			for line in lines:
				print(line)

			return
		seqNum = int(lines[1].split(' ')[1])
		
		# Process only if the server reply's sequence number is the same as the request's
		# match the request and reponse seq like lab wireshark
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID can assign to any other session
			if self.sessionId == 0:
				self.sessionId = session
			
			# Process only if the session ID is the same
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200: 
					#OK CODE
					if self.requestSent == self.SETUP:
						#-------------
						# TO COMPLETE
						#-------------
						# Update RTSP state.
						self.state = self.READY
						# Open RTP port.
						self.openRtpPort()
						#set time out for session
					elif self.requestSent == self.PLAY:
						self.state = self.PLAYING
					elif self.requestSent == self.PAUSE:
						self.state = self.READY
						# The play thread exits. A new thread is created on resume.
						self.playEvent.set()
					elif self.requestSent == self.TEARDOWN:
						self.state = self.INIT
						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1
					elif self.requestSent == self.BACKWARD:
						self.frameNbr = max(self.frameNbr - 50, 0)
						self.expFrameNbr = max(self.expFrameNbr - 50, 0)
					elif self.requestSent == self.FORWARD:
						self.expFrameNbr = self.expFrameNbr + 50
						# if to end of video, exp = max frame
				#else: pass
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		#-------------
		# TO COMPLETE
		#-------------
        # Create a new datagram socket to receive RTP packets from the server
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		# Set the timeout value of the socket to 0.5sec
		self.rtpSocket.settimeout(0.5)

		try:
			# Bind the socket to the address using the RTP port given by the client user
			self.rtpSocket.bind(("", self.rtpPort))
		except:
			tkinter.messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' % self.rtpPort)

	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		self.pauseMovie()
		if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()
		else: # When the user presses cancel, resume playing.
			self.playMovie()
