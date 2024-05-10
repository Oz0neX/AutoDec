from tkinter import Tk     # from tkinter import Tk for Python 3.x
from tkinter.filedialog import askopenfilename, askdirectory
from tkinter.messagebox import showerror
import traceback
import logging
import enum
import re
import fitz
import os

#Note: If any of the test numbers are not 50 or 15, display to user that it must be done manually.
#TODO:
# - Make the inner number match with number of questions..?
# --- If you change the "value correct" marker, it should adjust the real # of correct, then there would be no need for templates.

class Letter(enum.Enum):
    A = str.encode("\x01")
    B = str.encode("\x02")
    C = str.encode("\x04")
    D = str.encode("\x08")
    E = str.encode("\x10")
    X = str.encode("\x00")

# REMINDER: Before adding a new template, set all letter options of APKY to 'E'
class Size(enum.Enum):
    Large = {"File": 'Template50.apky', "Upperbound": 6000, "Lowerbound": 0} # Regular Test
    Medium = {"File": 'Template35.apky', "Upperbound": 4900, "Lowerbound": 4230} #TODO: Math template
    SmallMax = {"File": 'Template25.apky', "Upperbound": 4900, "Lowerbound": 4225} # Focus Quiz 16+
    Small = {"File": 'Template15.apky', "Upperbound": 4900, "Lowerbound": 4225} # Focus Quiz

class Test:
    def __init__(self, sizeTemplate):
        self.template = sizeTemplate.value
        self.fileStream = open(self.template["File"], 'rb')

        bytesList = []
        while True:
            byte = self.fileStream.read(1)
            bytesList.append(byte)
            if not byte:
                break
        self.bytesList = bytesList

        self.answers = []
        self.loadAnswers()

    # REMINDER: Set all letter options of APKY to 'E'
    # Sets the self.answers dict so answers can be loaded into memory.
    # Load bytes from file -> change in memory [...] -> set bytes to file
    def loadAnswers(self):
        questionNum = 0
        lastAnswer = 0
        foundAnswers = False

        for i in range(len(self.bytesList)):
            currentByteSize = int.from_bytes(self.bytesList[i], "little")
            bounded = (self.template["Lowerbound"] < i and i < self.template["Upperbound"])

            if bounded and currentByteSize == int.from_bytes(Letter.E.value, "little"):
                if (i - lastAnswer) < 6:
                    foundAnswers = True
                    questionNum += 1
                    self.answers.append({ # Question Dict
                        "Number": questionNum,
                        "BytePosition": lastAnswer,
                        "Letter": Letter.E
                    })
                elif foundAnswers:
                    questionNum += 1
                    self.answers.append({ # Question Dict
                        "Number": questionNum,
                        "BytePosition": lastAnswer,
                        "Letter": Letter.E
                    })
                lastAnswer = i
    
    # Set an answer for a question number (e.g. {"Number": 14, "Letter": Letter.D} to change the answer to D)
    def setAnswer(self, answer):
        for i in range(len(self.answers)):
            if (self.answers[i]["Number"] == answer["Number"]):
                self.answers[i]["Letter"] = answer["Letter"]

    def setSize(self, size):
      for i in range(len(self.answers)):
        if (i >= size):
          self.answers[i]["Letter"] = Letter.X

    # Creates a new test key with the altered letters
    def newTestKey(self, name):
        for x in self.answers:
          self.bytesList[x["BytePosition"]] = x["Letter"].value

        result = open(name + ".apky", "wb")
        bytestring = bytes()

        for x in self.bytesList:
            bytestring += x

        result.write(bytestring)
        result.close()

    def close(self):
        self.fileStream.close()

class AnswerGuide:
  def __init__(self, pdfPath):
    # Initialize templates for apky copy
    self.test50 = Test(Size.Large)
    self.test35 = Test(Size.Medium) # Temporarily is 50
    self.test25 = Test(Size.Medium)
    self.test15 = Test(Size.Small)

    with fitz.open(pdfPath) as doc:  # open document
        txt = chr(12).join([page.get_text() for page in doc])

    self.name = os.path.splitext(os.path.basename(pdfPath))[0]
    self.text = txt
    self.tests = []

  # Loop through the answer guides and save all keys into an array
  def createLocalKeys(self):
    regex = re.search("[\r\n]+[0-9]{1,2}\. [A-E]", self.text)
    letter = regex.group()[-1]
    keys = []
    currentTest = 0
    questionNumber = 1

    while regex is not None:
      if (questionNumber == 1):
        currentTest += 1
        keys.append([])

      keys[currentTest-1].insert((questionNumber-1), {"Number": questionNumber, "Letter": Letter[letter]})
      startIndex = regex.span()[1]
      self.text = self.text[startIndex::]

      regex = re.search("[\r\n]+[0-9]{1,2}\. [A-E]", self.text)
      if regex is not None:
        questionNumber = int(re.search("[0-9]{1,2}", regex.group()).group())
        letter = regex.group()[-1]

    for i in range(len(keys)):
      keySize = len(keys[i])
      if ((keySize) != 50) and (keySize != 35) and (keySize != 15):
         print("Non-traditional key count of " + str(keySize) + " on Test #" + str(i+1) + ", create test manually")
    self.tests = keys

  def chooseTemplate(self, keySize):
    if (keySize <= 15):
      #print("Focus Quiz Template")
      return self.test15
    elif (keySize <= 25):
      #print("Focus Quiz Max Template")
      return self.test25
    elif (keySize <= 35):
      #print("Math Test Template")
      return self.test35
    elif (keySize <= 50):
      #print("Normal Test Template")
      return self.test50

  def createApky(self):
    # Change each key into apky's
    path = askdirectory(title="Choose a folder for keys")
    if (len(path) == 0):
      showerror(title="ERROR: No folder specified", message="Must select a folder to save the keys to, exiting...")
      self.close()
      exit()
    count = 0
    for key in self.tests:
      test = self.chooseTemplate(len(key))
      count += 1
      for question in key:
        test.setAnswer({"Number": question["Number"], "Letter": question["Letter"]})
      
      test.setSize(len(key))
      test.newTestKey(path + "/"+ self.name + " " + str(count))
    
    self.close()
  
  def printKeys(self):
    # For debugging
    count = 0
    for x in self.tests:
      count += 1
      print("\n\n\tKey #" + str(count) + "\n")
      print(x)

  def close(self):
    self.test50.close()
    self.test35.close()
    self.test25.close()
    self.test15.close()

Tk().withdraw()

try:
  filename = askopenfilename(title="Upload an Answer Key", filetypes=[("PDF files", ".pdf")]) # show an "Open" dialog box and return the path to the selected file
  if (len(filename) == 0):
    showerror(title="ERROR: Missing answer PDF", message="Must select a PDF to read answers from. exiting...")
    exit()
  answerGuide = AnswerGuide(filename)
  answerGuide.createLocalKeys()
  #answerGuide.printKeys()
  answerGuide.createApky()
except Exception as e:
  showerror(title="ERROR: Internal Program Error", message=(traceback.format_exc()))

# \x01 = A
# \x02 = B
# \x04 = C
# \x08 = D
# \x10 = E