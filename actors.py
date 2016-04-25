# Library imports
import pykka
from pykka import ActorRegistry
import rtmidi.midiutil as midiutil
from threading import Timer
import Tkinter as tk

# Project imports
from euclid import euclidean_rhythm

class TimingActor(pykka.ThreadingActor):
    def __init__(self):
        # Make this thread a daemon so it ends when the main thread exits
        super(TimingActor, self).__init__(use_daemon_thread=True)
        self.playing = False

    def tick(self, count):
        if self.playing:
            self.target.tell({'type': 'tick'})
            Timer(self.period, self.tick, args=[count+1]).start()

    def on_receive(self, msg):
        if msg['type'] == 'config':
            # Set the sixteenth note period for this Actor
            self.period = 1.0/msg['bpm']*60.0 / 4.0

            # Get NoteActor URN
            self.target = ActorRegistry.get_by_urn(msg['target'])
            self.tick(0)
        elif msg['type'] == 'play': self.playing = True; self.tick(0)
        elif msg['type'] == 'stop': self.playing = False

class NoteActor(pykka.ThreadingActor):
    def __init__(self):
        # Make this thread a daemon so it ends when the main thread exits
        super(NoteActor, self).__init__(use_daemon_thread=True)
        self.midi_out, self.midi_out_name = midiutil.open_midiport(
            port='loop', 
            type_='output')

        self.seq = [{'i': 0, 'r': euclidean_rhythm(0,0), 'n': 60}, 
                    {'i': 1, 'r': euclidean_rhythm(0,0), 'n': 61}, 
                    {'i': 2, 'r': euclidean_rhythm(0,0), 'n': 62}, 
                    {'i': 3, 'r': euclidean_rhythm(0,0), 'n': 63},
                    {'i': 4, 'r': euclidean_rhythm(0,0), 'n': 64},
                    {'i': 5, 'r': euclidean_rhythm(0,0), 'n': 65}]

        self.mutes = [False]*len(self.seq)

    def send(self, s):
        if next(s['r']) and not self.mutes[s['i']]:
            self.gui_target.tell({'type': 'show', 'seq_num': s['i']})
            self.midi_out.send_message([144, s['n'], 100])
            Timer(0.05, self.note_off, args=[s['n'], s['i']]).start()

    def note_off(self, note_num, seq_num):
        self.midi_out.send_message([144, note_num, 0])
        if not self.mutes[seq_num]:
            self.gui_target.tell({'type': 'unshow', 'seq_num': seq_num})

    def on_receive(self, msg):
        if msg['type'] == 'config':
            self.gui_target = ActorRegistry.get_by_urn(msg['gui_target'])
        elif msg['type'] == 'seq-config':
            # Reset the Euclidean rhythm at seq_num using the parameters k and n
            self.seq[msg['seq_num']] = {'i': msg['seq_num'],
                                        'r': euclidean_rhythm(msg['k'], msg['n']), 
                                        'n': self.seq[msg['seq_num']]['n']}
        elif msg['type'] == 'seq-mute':
            self.mutes[msg['seq_num']] = not self.mutes[msg['seq_num']]
            self.gui_target.tell({'type': 'show-mute', 
                                  'seq_num': msg['seq_num'], 
                                  'muted': self.mutes[msg['seq_num']]})
        elif msg['type'] == 'tick': 
            map(self.send, self.seq)

class GuiActor(pykka.ThreadingActor):
    def __init__(self, root, timing_act_urn, note_act_urn):
        # Make this thread a daemon so it ends when the main thread exits
        super(GuiActor, self).__init__(use_daemon_thread=True)
        self.widgets = []

        # Set up transport controls
        timing_actor = ActorRegistry.get_by_urn(timing_act_urn)
        def make_transport_cb(msg):
            return lambda: timing_actor.tell({'type': msg})

        frame = tk.Frame(root, padx=5)
        play_b = tk.Button(frame, width=5, text='Play')
        stop_b = tk.Button(frame, width=5, text='Stop')
        play_b.config(command=make_transport_cb('play'))
        stop_b.config(command=make_transport_cb('stop'))
        # play_b.config(command=lambda: timing_actor.tell({'type': 'play'}))
        # stop_b.config(command=lambda: timing_actor.tell({'type': 'stop'}))

        play_b.grid(row=0, column=0, padx=10, pady=10)
        stop_b.grid(row=1, column=0, padx=10, pady=10)
        frame .grid(row=0, column=0)

        # Set up tk GUI
        # Create each sequencer frame
        note_actor = ActorRegistry.get_by_urn(note_act_urn)
        seq_names = ['Kick', 'Snare', 'Cl. HiHat', 'Op. HiHat', 'Clave', 'Cowbell']
        for idx in range(6):
            frame = tk.Frame(root, borderwidth=1, padx=5, relief=tk.RIDGE)
            seq_label = tk.Label (frame, text=seq_names[idx])
            k_label   = tk.Label (frame, text='k:')
            k_entry   = tk.Entry (frame, width=5)
            n_label   = tk.Label (frame, text='n:')
            n_entry   = tk.Entry (frame, width=5)
            start_b   = tk.Button(frame, width=7, text='Start')
            mute_b    = tk.Button(frame, width=7, text='Mute')

            # Capture the current sequence index, sequence k Entry object,
            # and sequence n Entry object with a closure in order to keep
            # references to them in the callback for this start button
            def make_start_cb(seq_idx, seq_k, seq_n):
                # Send a message to the NoteActor with the info
                # from this sequence's config frame
                return lambda: note_actor.tell({'type': 'seq-config', 
                                                'seq_num': seq_idx, 
                                                'k': int(seq_k.get()), 
                                                'n': int(seq_n.get())})
            start_b.config(command=make_start_cb(idx, k_entry, n_entry))

            # Capture the current sequence index, with a closure to use them
            # in a callback for the mute button
            def make_mute_cb(seq_idx):
                return lambda: note_actor.tell({'type': 'seq-mute', 
                                                'seq_num': seq_idx})
            mute_b.config(command=make_mute_cb(idx))

            seq_label.grid(row=0, column=0, columnspan=2)
            k_label  .grid(row=1, column=0, padx=5)
            n_label  .grid(row=2, column=0, padx=5)
            k_entry  .grid(row=1, column=1)
            n_entry  .grid(row=2, column=1)
            start_b  .grid(row=3, column=0, pady=5, columnspan=2)
            mute_b   .grid(row=4, column=0, pady=5, columnspan=2)

            frame.grid(row=0, column=idx+1)
            self.widgets.append([frame, seq_label, k_label, n_label])

    def show_playing(self, widgets):
        map(lambda w: w.config(bg='green'), widgets)

    def show_muted(self, widgets):
        map(lambda w: w.config(bg='red'), widgets)

    def display_off(self, widgets):
        map(lambda w: w.config(bg='SystemButtonFace'), widgets)

    def on_receive(self, msg):
        if msg['type'] == 'show':
            self.show_playing(self.widgets[msg['seq_num']])
        elif msg['type'] == 'unshow':
            self.display_off(self.widgets[msg['seq_num']])
        elif msg['type'] == 'show-mute':
            if msg['muted']:
                self.show_muted(self.widgets[msg['seq_num']])
            else:
                self.display_off(self.widgets[msg['seq_num']])

