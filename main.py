# Library imports
import Tkinter as tk

# Project imports
from actors import TimingActor, NoteActor, GuiActor

if __name__ == '__main__':
    root = tk.Tk()
    root.wm_title('Euclidean sequencer')
    root.wm_resizable(0,0)
    root.iconbitmap('favicon.ico')

    # Set up Actors
    timing_actor = TimingActor.start()
    note_actor   = NoteActor  .start()
    gui_actor    = GuiActor   .start(root, 
                                     timing_actor.actor_urn, 
                                     note_actor  .actor_urn)

    timing_actor.tell({'type': 'config', 'bpm': 120,
                       'target': note_actor.actor_urn})
    note_actor  .tell({'type': 'config',
                       'gui_target' : gui_actor.actor_urn})

    root.mainloop()

    # End TimingActor and NoteActor after tk's main loop ends
    gui_actor.stop(); note_actor.stop(); timing_actor.stop(); 
    exit()
