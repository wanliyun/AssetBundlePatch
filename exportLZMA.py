import lzma
import lz4


class Stream:
	def __init__(self, content):
		self.content = content
		self.position = 0
	
	def readInt8(self):
		ret = self.content[self.position]
		self.position += 1
		return ret


	def readInt16(self):
		a = self.content[self.position]
		b = self.content[self.position+1]
		self.position += 2
		return a<<8 | b

	def readInt32(self):
		a = self.content[self.position]
		b = self.content[self.position+1]
		c = self.content[self.position+2]
		d = self.content[self.position+3]
		self.position += 4
		return a<<24 | b<<16 |c<<8 |  d

	def readInt64(self):
		a = self.content[self.position]
		b = self.content[self.position+1]
		c = self.content[self.position+2]
		d = self.content[self.position+3]
		e = self.content[self.position+4]
		f = self.content[self.position+5]
		g = self.content[self.position+6]
		h = self.content[self.position+7]

		self.position += 8
		return a<<56 | b<<48 |c<<40 |  d<<32 | e<<24 | f<<16 | g<<8 | h

	def readString(self):
		startPos = self.position
		while self.content[self.position] != 0:
			self.position += 1

		retStr = self.content[startPos : self.position]
		self.position += 1
		return retStr

	def readRaw(self,len):
		retStr = self.content[self.position : self.position + len]
		self.position += len
		return retStr

	def readBlock(self, flag,compressSize,unCompressSize = -1):
		flag &= 0x3f
		bRawBytes = None

		
		if flag == 1:
			p0 = self.readInt8()
			p1 = self.readInt8()
			p2 = self.readInt8()
			p3 = self.readInt8()
			p4 = self.readInt8()
			content = self.readRaw(compressSize - 5)

			lc = p0 % 9
			remainder = int(p0 / 9)
			lp = remainder % 5
			pb = int(remainder / 5)

			dict_size = (p1) | (p2 << 8) | (p3 << 16) | (p4 << 32)

			filter = {
					"lc" : lc, "lp" : lp,	"pb" : pb,	"dict_size" : dict_size,
				}
			my_filters = [
				{"id": lzma.FILTER_LZMA1, "lc" : lc, "lp" : lp,	"pb" : pb,	"dict_size" : dict_size,},
				#{"id": lzma.FILTER_LZMA2, "lc" : lc, "lp" : lp,	"pb" : pb,	"dict_size" : dict_size,},
			]

			bRawBytes = lzma.decompress(content,lzma.FORMAT_RAW,None,my_filters)
		elif flag == 2 or flag == 3:
			content = self.readRaw(compressSize)
			bRawBytes = lz4.block.decompress(content, unCompressSize)
		else:
			bRawBytes = self.readRaw(compressSize)
		return bRawBytes

def export(inFile,outFile):
	f = open(inFile, "rb")
	content = f.read()
	f.close()

	ss = Stream(content)
	signure = ss.readString()
	format = ss.readInt32()
	engine = ss.readString()
	version = ss.readString()
	bundleSize = ss.readInt64()
	compressedSize = ss.readInt32()
	uncompressedSize = ss.readInt32()
	flag = ss.readInt32()

	blockInfos = ss.readBlock(flag,compressedSize,uncompressedSize)
	ssb = Stream(blockInfos)
	ssb.position = 0x10

	blockcount = ssb.readInt32()
	blockList = []
	for i in range(0,blockcount):
		bUSize = ssb.readInt32()
		bSize = ssb.readInt32()
		bFlag = ssb.readInt16()
		blockContent = ss.readBlock(bFlag, bSize, bUSize)
		blockList.append(blockContent)

	f = open(outFile,"wb")
	f.write(b"".join(blockList))
	f.close()

export("d:\\assetbundle\\test.ab","d:\\assetbundle\\test.ab.u")