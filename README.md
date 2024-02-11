# openmpt-houdini-importer

## Intro
This is a two-part project:

Part one is a modified `openmpt123` executable binary - something that usually ships with an OpenMPT distribution, (here, the hpp and cpp files are provided which you'll need to swap-in and then build the binary using the build system that comes with OpenMPT).

Part two is a Houdini Digital Asset ("HDA") with accompanying python module source, that is intended to allow one to 'import' tracker-module music files into Houdini for lots of fun visualising the music! 

It's only been built and tested on Gentoo Linux so far! I expect it might need some adaptation to work on some linuxes or windows/mac.

## Motivation
I am a huge fan of the demoscene (http://www.pouet.net) and tracked music (https://modarchive.org/) discovering Scream Tracker by The Future Crew back in 1992 or so, and I wrote a bunch of wierd old tracks myself, some of which I still rather like and I've always wanted to be able to make detailed and tightly synchronised visualisations for them.. producing something like a cross between a YT visualiser and a demoscene production, but not necessarily realtime. That's the motivation for this project!

## The HDA
The HDA runs the modified `openmpt123` binary (once told its location) to produce a flac audio rendering of the specified tracker-music module file (later also transcoded to wav using assumed-system-level availability of ffmpeg!), and simultaneously records a 'pattern log' text-file via the command's standard text output (stdout) and redirecting stdout via a pipe (`>`) to a file. The pattern-log records in reasonable temporal-detail: Millisecond precision for the moment - what pattern rows were played and when.

The HDA then does a rough kind of 'parsing' of each line in the pattern log.. and some additional processing like tracking when the last note-hit in a channel was, and then saves it all as a bunch of keyframes in various parms and multiparms on the HDA.

### Python Module
The file openmptImport.py needs to go somewhere on the python path. For Houdini this includes the 'Houdini settings' area in the user's homedir, like ~/houdini20.0/python3.10libs. One can create this subdirectory if it does not exist and copy the python file there, which should make it available for import in Houdini (you will need to restart the session if the directory did not previously exist). Note that for older Houdini versions the directory might be named a different python version like 'python2.7libs'.

### Installing the HDA:
Similarly to the python file, The HDA file can be copied into the houdini settings area in your home directory, but in this case into the 'otls/' subdirectory like ~/houdini20.0/otls (the example assumes you're on Houdini 20.0, update accordingly to whatever version you are using if on a different version). 

It is also possible to install the HDA into the current hip session without copying it anywhere, but be aware it will need to stay in that location in order for it to continue to be found when opening the hipfile. If that's a concern one way out of it is to unlock the HDA before saving, or to turn on the option in Asset Manager->Configuration to embed HDAs into hipfiles.

### Using the HDA:
The 'Module File' parameter can be used to specify which track you want to import, you should check the 'Output Dir' parameter before pressing any buttons however, and make sure it's somewhere it's ok to write stuff. Additionally the 'OpenMPT Executable' parm should be filled out with the path to the openmpt123 executable file that was built. The 'Add to LD Library Path' parm should be pointed at the directory containing the executable too, so that it can find its shared-libs. Once all of that is done, you can press the 'Write Outputs' button to write a flac and transcode it to wav (assuming system-wide availability of ffmpeg) and additionally a 'pattern-log' file.

Once that's done the audio can be added to the Houdini timeline by specifying a Chop node inside the hda as the 'realtime' audio source in the 'Audio Panel'. An example path for the Chop might be /obj/openmpt_import/chopnet1/AUDIO_OUT if the HDA was instantiated directly in /obj. There is a 'Get Length' button along with a 'Set Hip' button to get the playbar set to the correct length (occasionally the result still seems to need adjustment).

The pattern data can then be imported by pressing the 'Read Pattern Log' button, which creates lots of other data on the HDA node, that is read and used by the visualisers.

### Visualisers

The HDA also contains several prototype visualiser sop subnetworks:

* Something like 'Note Dots': Spheres that set their Y position based on their note value. Now spread over space so the camera can zoom along with the action.
* Note dot-trails.. pregenerated for the whole timeline and then colored/Alpha'd dynamically to reveal as the track progresses (so they stay realtime)
* Draw the scrolling text of the pattern log as copies of packed character-glyphs, and is set up to be as performant as I've been able to work out so far.. (one can write the grid out for the entire track, and then later, blast out the bit you want to see right now..)
* Chops-based sound spectrum visualiser with 'scrolling back over time' kinda vibe.
* Chops-based pulsing background-color-level via a large sphere.. This made YouTube's video codec kinda angry I think.. need to revisit!

## Youtube Link(s):
Many more kinds of visualisation are planned, but see my YouTube channel 'DanWills' for further examples, here's a recent one:
https://www.youtube.com/watch?v=4WMXwquRiWE

I'll also do a 'how to use this' desktop recording with voice-over before long too.
