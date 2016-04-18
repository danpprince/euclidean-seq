from __future__ import print_function

from itertools import cycle
import pykka
from pykka import ActorRegistry
import rtmidi.midiutil as midiutil
from threading import Timer
import time

# Where n is the number of steps in the rhythm and k is the number
# of "ones" in the rhythm
def euclidean_rhythm(k,n):
    # If either parameter is zero, return a generator that always returns zero
    if k == 0 or n == 0: return cycle([0])

    # m is the number of "zeros" in the rhythm
    m = n-k
    zeros, ones = [m], [k]

    def euclid(m,k,steps):
        if k == 0 or zeros[0] == 0: 
            return map(lambda x: x+[0]*(zeros[0]/ones[0]), steps)
        else:      
            zeros[0] = zeros[0]-k
            return euclid(k,m%k,map(lambda x: x+[0], steps[:k]) + steps[k:])

    return cycle(reduce(lambda x,y: x+y, 
                 euclid(max(k,m), min(k,m), [[1]]*k)))

class TimingActor(pykka.ThreadingActor):
    def __init__(self):
        # Make this thread a daemon so it ends when the main thread exits
        super(TimingActor, self).__init__(use_daemon_thread=True)

    def tick(self, count):
        self.target.tell({'from': 'timing', 'type': 'tick'})
        Timer(self.period, self.tick, args=[count+1]).start()

    def on_receive(self, msg):
        if msg['from'] == 'main' and msg['type'] == 'config':
            # Set the sixteenth note period for this Actor
            self.period = 1.0/msg['bpm']*60.0 / 4.0

            # Get NoteActor URN
            self.target = ActorRegistry.get_by_urn(msg['target'])
            self.target.tell({'from': 'timing', 'type': 'reset'})
            self.tick(0)

class NoteActor(pykka.ThreadingActor):
    def __init__(self):
        # Make this thread a daemon so it ends when the main thread exits
        super(NoteActor, self).__init__(use_daemon_thread=True)
        self.midi_out, self.midi_out_name = midiutil.open_midiport(
            port='loop', 
            type_='output')

        self.seq = [[euclidean_rhythm( 1, 4), 60], 
                    [euclidean_rhythm( 3,16), 61], 
                    [euclidean_rhythm(33,64), 62], 
                    [euclidean_rhythm( 3,16), 63],
                    [euclidean_rhythm( 7,32), 64]]

    def send(self, s):
        if next(s[0]):
            self.midi_out.send_message([144, s[1], 100])
            Timer(0.05, self.note_off, args=[s[1]]).start()

    def note_off(self, note_num):
        self.midi_out.send_message([144, note_num, 0])

    def on_failure(self, exception_type, exception_value, traceback):
        print('NoteActor error: {}; {}'.format(exception_type, exception_value))
        print(traceback)

    def on_receive(self, msg):
        if msg['from'] == 'timing' and msg['type'] == 'reset': 
            print('resetting NoteActor')
        elif msg['from'] == 'main' and msg['type'] == 'config':
            # Reset the Euclidean rhythm at seq_num using the parameters k and n
            print('Modifying sequence {}: k={}, n={}'
                  .format(msg['seq_num']), msg['k'], msg['n'])
            self.seq[msg['seq_num']] = [euclidean_rhythm(msg['k'], msg['n']), 
                                        self.seq[msg['seq_num']][1]]
        elif msg['from'] == 'main':
            print('msg from main: {}'.format(msg))
        elif msg['from'] == 'timing' and msg['type'] == 'tick': 
            map(self.send, self.seq)

if __name__ == '__main__':
    timing = TimingActor.start()
    note   = NoteActor  .start()

    timing.tell({'from': 'main', 'type': 'config', 
                 'bpm': 120, 'target': note.actor_urn})

    # Keep the main thread alive until keyboard exception
    try: 
        while True: 
            time.sleep(0.1)
            s = raw_input('Configure sequence num, k, n: ')
            s_num, k, n = map(int, s.split())
            print(s_num, k, n)
            note.tell({'from': 'main', 'type': 'config', 
                       'seq_num': s_num, 'k': k, 'n': n})
    except ValueError:
        print('Error in configuration string')
    except:
        timing.stop(); note.stop(); exit()
