import sys,pygame,os
from binascii import unhexlify

from Py2D.Py2D import *

# This function was shamelessly stolen from http://stackoverflow.com/questions/8730927/convert-python-long-int-to-fixed-size-byte-array
def long_to_bytes (val, endianness='big'):
    """
    Use :ref:`string formatting` and :func:`~binascii.unhexlify` to
    convert ``val``, a :func:`long`, to a byte :func:`str`.

    :param long val: The value to pack

    :param str endianness: The endianness of the result. ``'big'`` for
    big-endian, ``'little'`` for little-endian.

    If you want byte- and word-ordering to differ, you're on your own.

    Using :ref:`string formatting` lets us use Python's C innards.
    """

    # one (1) hex digit per four (4) bits
    width = val.bit_length()

    # unhexlify wants an even multiple of eight (8) bits, but we don't
    # want more digits than we need (hence the ternary-ish 'or')
    width += 8 - ((width % 8) or 8)

    # format width specifier: four (4) bits per hex digit
    fmt = '%%0%dx' % (width // 4)

    # prepend zero (0) to the width, to zero-pad the output
    s = unhexlify(fmt % val)

    if endianness == 'little':
        # see http://stackoverflow.com/a/931095/309233
        s = s[::-1]

    return s


# Constants and shit
MAGIC="AUTO"
START_BYTE="S"
EOF_BYTE=0x0
SECTION_END_BYTE="E"
HEADER_SECTION_START_BYTE="H"
INSTRUCTION_START_BYTE="I"
INSTRUCTION_SET_START_BYTE="T" # Chosen because I'm running out of bytes
COMMAND_END_BYTE=","

# Think of all the buttons we can support with this! :D
BUTTON_ID=0x1000
AXIS_ID=0x2000

def genHeader(data):
    return HEADER_SECTION_START_BYTE + long_to_bytes(len(data)) + SECTION_END_BYTE

def buildInstructionSet(data):
    instruction_set = []
    for instr in data:
        instruction = "" # Should be a string of bytes NOTHING ELSE SHOULD BE IN THIS
        for com in instr:
            t = type(com)
            fcom = com
            if(t == float or t == int):
                # Keep first 3 decimal places
                # Do the same with ints, so that we just divide all by 1000 regardless
                # now we don't need to worry about the type
                fcom = int(1000*com)

                # Meduka
                # What is it Coobie?
                # Become Meguca
                fcom = long_to_bytes(fcom)
            fcom += COMMAND_END_BYTE
            instruction += fcom
        instruction_set.append(instruction)
    return instruction_set

# Start Instruction set
# Start Instruction (command set)
# Each command ends with ','
# Instruction ends when E is seen
# TI{com1},{com2},{com3},{etc...}E{etc...}E
# Paste all of the instructions together
def formatInstructions(i_list):
    formatted = "" + INSTRUCTION_SET_START_BYTE
    for instr in i_list:
        formatted += INSTRUCTION_START_BYTE + instr + SECTION_END_BYTE
    formatted += SECTION_END_BYTE
    return formatted

def writeJoystickFile(filename,data,overwriteIfExists=False):
    if os.path.exists(filename) and not overwriteIfExists:
        raise OSError("%s already exists!"%filename)

    all_data = ""
    header = genHeader(data) # String
    instrs = buildInstructionSet(data) # List
    finstrs = formatInstructions(instrs) # String

    all_data = MAGIC+header+finstrs+EOF_BYTE # String

    f = open(filename,'wb')
    f.write(all_data)
    f.close()

class TimerRecorder(Timer.Timer):
    def __init__(self):
        Timer.Timer.__init__(self,-1)
        self.record = []
    def _timer(self):
        while True:
            self.ctime = pygame.time.get_ticks()
            if self.timing:
                if self.ctime-self.lastTime >= 1:
                    self.timed+=1
                    self.lastTime=self.ctime
    def recordTime(self):
        self.stopTimer()
        self.record.append(self.getTimePassed())
        self.reset()
        self.timing = False

class JoystickCapture(IterativeLoop.IterativeLoop):
    def __init__(self):
        IterativeLoop.IterativeLoop.__init__(self)
        self.joy = None
        self.board = None
        self.buttonTexts = []
        self.axisTexts = []
        self.joyText = Text.Text("Joystick 0",color=(255,255,255,255))
        self.tolerance = 0.0
        self.default_save_dir = ""
        self.timing_start = 0.0
        self.last_time = 0.0

        self.axislists = []
        self.buttontimes = []

    def Init(self):
        self.getScreen().Init("./JoystickCapture.cfg")
        self.tolerance = self.getScreen().settings.getOption("Tolerance")
        self.default_save_dir = self.getScreen().settings.getOption("DefaultSaveDirectory")
        pygame.joystick.init()
        self.board = Inputs.Keyboard.Keyboard()
        self.joy = pygame.joystick.Joystick(0) 
        self.joy.init()
        for i in range(self.joy.get_numbuttons()):
            self.buttonTexts.append(Text.Text("Button%d="%i,color=(255,255,255,255)))
            self.buttonTexts[i].setPosY(self.buttonTexts[i].getFont().size("0")[1]*i)
            self.getScreen().addToQueue(self.buttonTexts[i])

            self.buttontimes.append([])

        for i in range(self.joy.get_numaxes()):
            self.axisTexts.append(Text.Text("Axis%d="%i,color=(255,255,255,255)))
            xoffset = self.axisTexts[i].getFont().size("0")[1]*len(self.buttonTexts)
            self.axisTexts[i].setPosY((self.axisTexts[i].getFont().size("0")[1]*i)+xoffset)
            self.getScreen().addToQueue(self.axisTexts[i])

            self.axislists.append([])


        self.timing_start = self.getScreen().getClock().get_rawtime()
        self.last_time = 0.0

    def Execute(self):
        for i in range(self.joy.get_numbuttons()):
            val = int(self.joy.get_button(i))

            # Only add a value if it hasn't already been added
            # Basically, alternate
            if val:
                if(self.buttonsTexts[i].getString() == "Button%d=0"%i):
                    self.buttontimes[i].append(self.getScreen().getClock())
            else:
                if(self.buttonTexts[i].getString() == "Button%d=1"%i):
                    self.buttontimes[i].append(self.getScreen().getClock())

            self.buttonTexts[i].setString("Button%d=%d"%(i,val))

        # Only update the axes every half a second
        if(int((self.getScreen().getClock().get_rawtime() - self.last_time)*10)/10.0 > 0.5):
            self.last_time = self.getScreen().getClock().get_rawtime()
            for i in range(self.joy.get_numaxes()):
                val = self.joy.get_axis(i)
                self.axisTexts[i].setString("Axis%d="%(i)+str(val))
                # Record the current joystick value
                axislists[i].append(val)

    def IsFinished(self):
        return self.board.getKeyOnce(pygame.K_ESCAPE) or pygame.event.peek(pygame.QUIT)

    def End(self):
        # Make sure we have an end time as well
        if(len(self.buttontimes)%2 != 0):
            self.buttontimes.append(self.getScreen().getClock().get_rawtime())

        # Turn the arrays into an array of [[ID,time],[ID,time],etc...]
        final_button_data = []
        for i in range(len(self.buttontimes)):
            for t in self.buttontimes[i]:
                # BIT SHIFTING! :D
                bid = BUTTON_ID|i
                final_button_data.append([bid,t])

        final_axis_data = []
        for i in range(len(self.axislists)):
            aid = AXIS_ID|i
            final_axis_data.append([aid,self.axislists[i]])

        # Combine the two sets of data and sort them
        final_total_data = sorted(final_axis_data+final_button_data)

        # Finally, write the joystick data to a file
        writeJoystickFile(os.path.join(self.default_save_dir,"test1.joy"),final_total_data,True)

START_WITHOUT_ERROR_HANDLING(JoystickCapture)

