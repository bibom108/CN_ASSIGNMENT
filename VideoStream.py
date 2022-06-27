
class VideoStream:
	def __init__(self, filename):
		self.filename = filename
		try:
			self.file = open(filename, 'rb')
			self.storedFilePos = [0]
		except:
			raise IOError
		self.frameNum = 0
		self.numberOfFrame = 0

	def backward(self):
		backwardFrame = 50
		self.numberOfFrame = self.frameNum
		if (self.numberOfFrame > backwardFrame):
			curFile = self.file.seek(self.storedFilePos[self.frameNum-backwardFrame],0)
			self.frameNum -= backwardFrame
			if (self.frameNum < 0):
				self.frameNum = 0
		else:
			curFile = self.file.seek(self.storedFilePos[0],0)
			self.frameNum = 0
		
		return self.nextFrame()
		
	def forward(self):
		"""Get next frame."""
		ForwardFrame = 50
		data = bytes()
		while (ForwardFrame > 0):
			self.nextFrame()
			ForwardFrame -= 1
		return self.nextFrame()


	def nextFrame(self):
		"""Get next frame."""
		data = self.file.read(5) # Get the framelength from the first 5 
		if data: 
			framelength = int(data)	
			# Read the current frame
			data = self.file.read(framelength)
			self.frameNum += 1
			if (self.frameNum == len(self.storedFilePos)):
				self.storedFilePos.append(self.file.tell())
				
		return data
		
	def frameNbr(self):
		"""Get frame number."""
		return self.frameNum
	
	