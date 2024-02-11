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
