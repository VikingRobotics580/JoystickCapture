import sys,pygame,os
from pygame.locals import *
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

AXIS_VAL_TOLERANCE = 10 #0.010

# Think of all the buttons we can support with this! :D
BUTTON_ID=0x1000
AXIS_ID=0x2000

USED_JOYSTICK_TYPES = [JOYBUTTONUP,JOYBUTTONDOWN,JOYAXISMOTION]

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

        self.input_list = []

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

        for i in range(self.joy.get_numaxes()):
            self.axisTexts.append(Text.Text("Axis%d="%i,color=(255,255,255,255)))
            xoffset = self.axisTexts[i].getFont().size("0")[1]*len(self.buttonTexts)
            self.axisTexts[i].setPosY((self.axisTexts[i].getFont().size("0")[1]*i)+xoffset)
            self.getScreen().addToQueue(self.axisTexts[i])

        self.timing_start = self.getScreen().clock.get_rawtime()
        self.last_time = 0.0

    def Execute(self):
        curr_time = self.getScreen().clock.get_rawtime()
        for i in range(self.joy.get_numbuttons()):
            val = int(self.joy.get_button(i))
            self.buttonTexts[i].setString("Button%d=%d"%(i,val))
        # Only update the axes every half a second
        if(int((self.getScreen().clock.get_rawtime() - self.last_time)*10)/10.0 > 0.5):
            self.last_time = self.getScreen().clock.get_rawtime()
            for i in range(self.joy.get_numaxes()):
                val = self.joy.get_axis(i)
                self.axisTexts[i].setString("Axis%d="%(i)+str(val))

        for event in pygame.event.get():
            if event.type in USED_JOYSTICK_TYPES:
                self.input_lists.append([event,curr_time])

    def IsFinished(self):
        return self.board.getKeyOnce(pygame.K_ESCAPE) or pygame.event.peek(pygame.QUIT)

    def End(self):
        instruction_section = INSTRUCTION_SET_START_BYTE
        num_instructions = 0
        header = ""
        last_btime = 0
        last_atime = 0

        for i in range(len(self.input_list)):
            if(self.input_list[i][0].type == JOYBUTTONUP):
                instr = INSTRUCTION_START_BYTE + long_to_bytes(BUTTON_ID|self.input_list[i][0].button)
                instr += COMMAND_END_BYTE + long_to_bytes(self.input_list[i][1]-last_btime) + INSTRUCTION_END_BYTE
                instruction_section += instr
                num_instructions+=1
            elif(self.input_list[i][0].type == JOYBUTTONDOWN):
                last_btime = self.input_list[i][1]
            elif(self.input_list[i][0].type == JOYAXISMOTION):
                dur = self.input_list[i][1] - last_atime
                last_atime = self.input_list[i][1]
                instr = INSTRUCTION_START_BYTE + long_to_bytes(AXIS_ID|self.input_list[i][0].axis)
                instr += COMMAND_END_BYTE + long_to_bytes(self.input_list[i][0].value) + COMMAND_END_BYTE
                instr += long_to_bytes(dur) + SECTION_END_BYTE
                instruction_section += instr
                num_instructions+=1
        instruction_section += SECTION_END_BYTE

        header = HEADER_SECTION_START_BYTE + long_to_bytes(num_instructions) + SECTION_END_BYTE

        totalData = MAGIC + header + instruction_section + EOF_BYTE
        open(os.path.join(self.default_save_dir,"test.joy"),'wb').write(totalData)

#if __name__ == "__main__":
START_WITHOUT_ERROR_HANDLING(JoystickCapture)

