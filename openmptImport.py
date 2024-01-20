import hou
import time
from datetime import datetime
import subprocess
import os
import fnmatch
import re

def isOpenMPTImportObject( tnode ):
    if not tnode :
        return False
    if tnode.type().category() != hou.objNodeTypeCategory() :
        return False
    if tnode.type().nameComponents()[2] != "openmpt_import" :
        return False
    return True

def getOpenMptImportNodeFromKwargs( kwargs ):
    if not kwargs :
        return None
    if not 'node' in kwargs :
        return None
    if not isOpenMPTImportObject( kwargs['node'] ) :
        return None
    return kwargs['node']
    
def testPlaybackButtonCallback(kwargs):
    ompt_node = getOpenMptImportNodeFromKwargs( kwargs )
    if not ompt_node :
        return
    testPlayback( ompt_node )

def amendLDLibraryPath( ld_lib_path_amend ) :
    ldlp = "LD_LIBRARY_PATH"
    if ldlp in os.environ :
        curr_ldlp = os.environ[ ldlp ]
        os.environ[ ldlp ] = curr_ldlp + ":" + ld_lib_path_amend
    else :
        os.environ["LD_LIBRARY_PATH"] = ld_lib_path_amend

def testPlayback( ompt_node ) :
    mod_file = ompt_node.evalParm("module_file")
    # Note: Assumption of getting float here:
    test_seconds = ompt_node.evalParm("seconds_of_playback")
    poll_frequency = ompt_node.evalParm("poll_frequency")
    openmpt_executable = ompt_node.evalParm("openmpt_executable")
    amendLibPathIfNeeded( ompt_node )
    
    test_cmd = [ openmpt_executable.encode(),
                 mod_file.encode() ]
    print( "Running command to test playback of module: " + mod_file )
    start_time = datetime.now()
    mpt_pope = subprocess.Popen( test_cmd, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE, )
    code,out,err = runForSeconds( mpt_pope, test_seconds, 
                                  poll_frequency, 
                                  terminate=True, 
                                  kill=True )

def getLengthButtonCallback(kwargs):
    ompt_node = getOpenMptImportNodeFromKwargs( kwargs )
    if not ompt_node :
        return
    getLength( ompt_node )
    
def setHipButtonCallback(kwargs):
    ompt_node = getOpenMptImportNodeFromKwargs( kwargs )
    if not ompt_node :
        return
    setHipRange( ompt_node )
    
def writePatternLogButtonCallback(kwargs):
    ompt_node = getOpenMptImportNodeFromKwargs( kwargs )
    if not ompt_node :
        return
    writePatternLog( ompt_node )

def renderOutputsButtonCallback(kwargs):
    ompt_node = getOpenMptImportNodeFromKwargs( kwargs )
    if not ompt_node :
        return
    renderOutputs( ompt_node )

def getBaseOpenMptCommand( ompt_node ):
    openmpt_executable = ompt_node.evalParm("openmpt_executable")
    if not openmpt_executable:
        return []
    return [ openmpt_executable.encode() ]

def setHipRange( ompt_node ):
    length = ompt_node.evalParm("seconds_of_playback")
    if not length:
        return
    hou.playbar.setTimeRange( 0.0, length )

def getLength( ompt_node ):
    mod_file = ompt_node.evalParm("module_file")
    openmpt_executable = ompt_node.evalParm("openmpt_executable")
    amendLibPathIfNeeded( ompt_node )
    ompt_cmd = getBaseOpenMptCommand( ompt_node )
    ompt_cmd.extend( [ b"--info",
                       mod_file.encode(), ] )
    plen_pope = subprocess.Popen( ompt_cmd, 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, )
    # don't really need a timeout here just can't be bothered changing it..
    returncode, stdout, stderr = runForSeconds( plen_pope, 99, 1, 
                                                terminate=True, 
                                                kill=True )
    stdout_str = [ byt.decode() for byt in stdout ]
    print("getLength got lines:\n" + "".join( stdout_str ))
    for line in stdout_str:
        if line.startswith("Duration"):
            lspl = line.split(":")
            if len(lspl) != 3 :
                continue
            mins = int( lspl[1].strip() )
            secs = float( lspl[2].strip() )
            total_secs = mins * 60.0 + secs
            ompt_node.parm("seconds_of_playback").set( total_secs )

# Not used any more: TODO: remove
def writePatternLog( ompt_node ):
    mod_file = ompt_node.evalParm("module_file")
    pattern_file = ompt_node.evalParm("pattern_log_file")
    openmpt_executable = ompt_node.evalParm("openmpt_executable")
    poll_frequency = ompt_node.evalParm("poll_frequency")
    test_seconds = ompt_node.evalParm("seconds_of_playback")
    update_ms = int( ompt_node.evalParm("update_ms") )
    
    amendLibPathIfNeeded( ompt_node )
    
    print("If this works, we'll have " + mod_file +
          "being pattern-logged to: " + pattern_file)
    
    ompt_cmd = getBaseOpenMptCommand( ompt_node )
    ompt_cmd.extend( [ b"--samplerate", b"48000",
                       b"--pattern",
                       b"--pattern-time-log",
                       b"--gain", b"-256",
                       b"--end-time", str( test_seconds ).encode(),
                       b"--assume-terminal",
                       b"--update", str( update_ms ).encode(),
                       mod_file.encode(), ] )
    start_time = datetime.now()
    
    combined_cmd = b" ".join( ompt_cmd ) \
                   + b" > " \
                   + pattern_file.encode()
    print( b"About to run combined command: " + combined_cmd )
    plog_pope = subprocess.Popen( combined_cmd, 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  shell=True )
    
    returncode, stdout, stderr = runForSeconds( plog_pope, test_seconds, poll_frequency, 
                                                terminate=True, 
                                                kill=True )
                   
def amendLibPathIfNeeded( ompt_node ):
    ldlibpath_amend = ompt_node.evalParm("add_to_ld_library_path")
    if ldlibpath_amend :
        print( "Amending LD_LIBRARY_PATH to include: " + str( ldlibpath_amend ) )
        amendLDLibraryPath( ldlibpath_amend )


def runForSeconds( a_pope, test_seconds, poll_frequency, terminate=False, kill=False ):
    # It's still a bit of a mystery to me how this terminates! 
    # is it asking for a returncode that does it?
    start_time = datetime.now()
    elapsed_seconds = 0.0
    poll = None
    progress = 0.0
    with hou.InterruptableOperation( operation_name="Generating outputs..", 
                                     long_operation_name="Rendering to wav and pattern log..",
                                     open_interrupt_dialog=True ) as hinterup:
        while elapsed_seconds < test_seconds and poll is None :
            curr_time = datetime.now()
            curr_delta = curr_time - start_time
            # Got a timedelta? think so..
            # Probably want float seconds! YEAH total_seconds() method!
            print( "Elapsed seconds: " + str( curr_delta.total_seconds() ) )
            elapsed_seconds = curr_delta.total_seconds()
            # print( str( curr_delta ) )
            #print( "Microseconds: " + str( curr_time.microseconds ) )
            
            time.sleep( poll_frequency )
            poll = a_pope.poll()
            #if poll :
            print( ".. and process.poll said: " + str( poll ) )
            # Total guess for now much to increment here.. 
            # however it's relative anyway.. so shouldn't
            # really be too misleading!
            relative_advance = 0.03
            progress = incrementProgress( progress, relative_advance )
            print( "Progress is now: " + str( progress ) )
            writeOutputsUpdateProgress( hinterup, progress, message=None, subprogress=None )
            
        print( "Final poll (zero means no-error!): " + str( poll ) )
        print( "Waited for about: " + str( elapsed_seconds ) )
    
        if terminate:
            a_pope.terminate()
        
        if kill:
            a_pope.kill()
        
    pope_returncode = a_pope.returncode
    print( "\nProcess ended, returncode was: " + str( pope_returncode ) )
    popeerr = a_pope.stderr.readlines()
    popeout = a_pope.stdout.readlines()
    
    #print( "pope stdout was: " + "".join( [ str(s) for s in popeout ] ) )
    #print( "pope error was: " + "".join( [ str(s) for s in popeerr ] ) )

    return pope_returncode, popeout, popeerr

def getOutputDirAndBasenameNoExt( ompt_node ):
    mod_file = ompt_node.evalParm("module_file")
    output_file = os.path.basename( mod_file )
    output_file_splitext = os.path.splitext( output_file )
    output_file_noext = output_file_splitext[0]
    output_dir = os.path.dirname( mod_file )
    use_alt_output_dir = bool( ompt_node.evalParm( "use_different_dir_for_output" ) )
    if use_alt_output_dir:
        output_dir = ompt_node.evalParm( "output_dir" )
    return output_dir, output_file_noext
        
def getWavOutputName( ompt_node ) :
    output_dir, output_file_noext = getOutputDirAndBasenameNoExt( ompt_node )
    output_wav_file = os.path.join( output_dir, output_file_noext + ".wav" )
    return output_wav_file
    
def getPatternLogOutputName( ompt_node ) :
    output_dir, output_file_noext = getOutputDirAndBasenameNoExt( ompt_node )
    output_patternlog_file = os.path.join( output_dir, output_file_noext + ".modlog" )
    return output_patternlog_file
    
def renderOutputs(ompt_node):

    # xmpl="openmpt123 --stdout --samplerate 44100 --channels 2 --no-float /home/dan/tracking/short_eltra_pan.it | sox -t raw -r 48k -e signed -b 16 -c 2 - output.wav"
    print( "renderOutputs: " + str( ompt_node ) )
    mod_file = ompt_node.evalParm("module_file")
    use_alt_output_dir = bool( ompt_node.evalParm("use_different_dir_for_output") )
    overwrite = bool( ompt_node.evalParm("overwrite") )
    
    write_pattern_log = bool( ompt_node.evalParm("write_pattern_log") )
    
    output_file = os.path.basename( mod_file )
    output_file_splitext = os.path.splitext( output_file )
    output_file_noext = output_file_splitext[0]
    output_dir = os.path.dirname( mod_file )
    
    if use_alt_output_dir:
        output_dir = ompt_node.evalParm("output_dir")
        
    if not os.path.isdir( output_dir ):
        raise hou.OperationFailed("Output dir is not a dir!")
        
    # TODO: allow writing directly to wav for ppl that have that codec..
    # I just tried things till one worked.. thankfully flac did!
    # ffmpeg can transcode to wav (or aiff) in a jiffy too.
    use_ext = "flac"
    output_sound_file = os.path.join( output_dir, output_file_noext + "." + use_ext )
    output_wav_file = os.path.join( output_dir, output_file_noext + ".wav" )
    if os.path.isfile( output_sound_file ) and overwrite:
        os.remove( output_sound_file )
    # openmpt123 will error if the file already exists!
    
    output_pattern_log_file = ""
    
    # ompt_node.evalParm("output_file")
    # Note: Assumption of getting float here:
    test_seconds = ompt_node.evalParm("max_seconds_to_wait")
    poll_frequency = ompt_node.evalParm("poll_frequency")
    openmpt_executable = ompt_node.evalParm("openmpt_executable")
    amendLibPathIfNeeded( ompt_node )
    update_ms = int( ompt_node.evalParm("update_ms") )
    
    ompt_cmd = [ openmpt_executable.encode(),
                 # Not sure if overriding samplerate or channels here is really 
                 # necessary..
                 # It's a bit of a holdover from when we previously used piping
                 # the output to sox.. which ended up being less than ideal for a 
                 # few reasons.. the main one being that the output seemed to 
                 # become mono! :/// turned out I think I was just using batch mode
                 # wrong before, silly me!
                 
                 # b"--samplerate", b"48000",
                 # b"--channels", b"2",
                 b"--batch", 
                 b"--output", output_sound_file.encode(),
                 mod_file.encode() ]
                 
    if write_pattern_log:
        output_pattern_log_file = getPatternLogOutputName( ompt_node )
        if os.path.isfile( output_pattern_log_file ) and overwrite:
            os.remove( output_pattern_log_file )
        ompt_cmd += [ b"--pattern",
                      b"--pattern-time-log",
                      b"--progress",
                      b"--update", str( update_ms ).encode(),
                      b">", output_pattern_log_file.encode() ]
                      
    if os.path.isfile( output_wav_file ) and overwrite:
        os.remove( output_wav_file )
    
    ompt_cmd += [ b"&&", b"ffmpeg", 
                  b"-i", output_sound_file.encode(),
                  output_wav_file.encode(), b">", b"/dev/null" ]
                
    #ompt_cmd = [ openmpt_executable.encode(),
    #             b"--stdout",
    #             b"--samplerate", b"48000",
    #             b"--channels", b"2",
    #             b"--no-float",
    #             mod_file.encode(), ]
                 
    #sox_cmd = [ b"sox", 
    #            b"-t", b"raw", 
    #            b"-r", b"48k", 
    #            b"-e", b"signed",
    #            b"-b", b"16",
    #            b"-c", b"2",
    #            b"-",
    #            output_file.encode() ]
                
    # Why did I end up with this!!? Flipping work the 
    # pipes out properly instead of this!
    combined_cmd = b" ".join( ompt_cmd )
    print( "Running combined command: " + combined_cmd.decode() )
    out_pope = subprocess.Popen( combined_cmd, 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 shell=True)
    
    returncode, stdout, stderr = runForSeconds( out_pope, test_seconds, poll_frequency )

def readPatternLogButtonCallback(kwargs):
    ompt_node = getOpenMptImportNodeFromKwargs( kwargs )
    if not ompt_node :
        return
    readPatternLog( ompt_node )

def lineLooksLikePreamble( line ):
    if line.startswith("openmpt123"):
        return True
    #print( "line: " + str(line) )
    #print( "line.startswith: " + str( line.startswith("Copyright") ) )
    if line.startswith("Copyright"):
        return True
    return False

def getModInfoRegex():
    return re.compile( "^([A-Za-z0-9_]+)\.*: (.*)$" )

def getLineModuleInfo( line ):
    # None when there isn't any!
    minf_regex = getModInfoRegex()
    match = minf_regex.match( line )
    return match

def stripPreambleLines( lines ):
    preamble_lines = []
    remaining_lines = []
    for ix,line in enumerate( lines ):
        # Ignore blank lines.. still trying to work out how to not get any!..
        if line.strip() == "":
            continue
        if lineLooksLikePreamble( line ) :
            # print("skipping preamble: " + str( line ) )
            preamble_lines.append( line )
        else :
            remaining_lines.append( line )
    return preamble_lines, remaining_lines

def stripAndExtractModuleInfoLines( lines ):
    pattern_lines = []
    minfo_lines = []
    info_dict = {}
    for ix,line in enumerate( lines ):
        if line.strip() == "":
            # Also ditch blank lines
            continue
        
        minfo = getLineModuleInfo( line )
        if minfo :
            info_name = minfo.groups()[0]
            info_value = minfo.groups()[1]
            info_dict[ info_name ] = info_value
            # Accumulate all used characters so we can make a map of them
            # and use instancing or whatever
            # And append to the minfo list instead:
            minfo_lines.append( line.strip() )
        else :
            pattern_lines.append( line.strip() )
    return minfo_lines, pattern_lines, info_dict

def getPatternRe() :
    return "^([A-G\\.=]{1}[-=#\\.]{1}[0-9=\\.]{1}) ([0-9A-F\\.]{2})([A-Za-z\\. ]{1}[0-9A-F\\.]{2}) ([A-Z0-9\\.]{1}[A-Z0-9\\.]{2})$"
def getLinePatternInfo( line ):
    # first split the line into order, columns and timeinfo,
    # print( "glpi line: " + line )
    row_re = re.compile("^(:*)([0-9]+)/(:*)([0-9]+)")
    rowmatch = row_re.match( line )
    if not rowmatch :
        return None, None
    colons = rowmatch.groups()[0]
    order = rowmatch.groups()[1]
    morecolons = rowmatch.groups()[2]
    row = rowmatch.groups()[3]
    # Patched order into the output since that might be handy
    # for visualising things too.
    
    # Discard the order/row bit now..
    order_n = int( order )
    row_n = int( row )
    
    prefix_len = len( colons ) + len( order ) + 1 + len( morecolons ) + len( row )
    if prefix_len > len( line ) :
        return None, None
    line = line[ prefix_len: ]
    # Now strip off the timestamp from the end
    # actual example at present: "Pos: 00:14.666 / 02:46.489   "
    
    time_re = re.compile("Pos: ([0-9]{2}\:[0-9]{2}\.[0-9]{3})")
        
    # For later to extract the pieces:
    # re.compile(".*([0-9]2)\:([0-9]+)\.([0-9]+).*")
    
    time_extract = time_re.findall( line )
    time_str = None
    if time_extract :
        line_spl = line.split("Pos:")[0]
        time_str = time_extract[0]
        #time_vals['secs'] = tg[1]
        #time_vals['ms'] = tg[2]
    if not time_str:
        return None, None
        
    pattern_vals = line.strip().split("  ")
    pattern_vals = [ pv.strip("+") for pv in pattern_vals ]
    # print( "Number of channel pattern vals is: " + str( len( pattern_vals ) ) )
    # then match the pattern vals:
    pattern_vals_matches = []
    for chix, pattern_val in enumerate( pattern_vals ) :
        # print( "Processing pattern_val: " + str( pattern_val ) )
        pat_re = re.compile( getPatternRe() )
        pmatch = pat_re.match( pattern_val )
        if pmatch :
            pattern_vals_matches.append( pmatch.groups() )
        else :
            if not pattern_val.startswith("Pos"):
                print("Pattern val did not match regex: " + str( pattern_val ))
                print( "regex was: " + getPatternRe() )
        #if pstrs :
        #    print( "Time: " + str( time_str) + " chan: " + str( chix ) + " pattern regex grouped: " + str( pstrs.groups() ) )
    return time_str, order_n, row_n, pattern_vals_matches
    
def getPatternInfo( lines, nchans ):
    """Get list of lines and info_dict (timeinfo and channels)
    see getLinePatternInfo()
    Returns:
        2-tuple (list, dict)
            The list of lines and the channel dict that resulted from 'parsing' 
            the input lines.
    """
    
    print( "getPatternInfo ninputlines: " + str( len( lines ) ) )
    newlines = []
    pattern_info_dict = {}
    row_info_dict = {}
    for ix,line in enumerate( lines ):
        # print("Considering line: " + line)
        if line.strip() == "":
            # Also ditch blank lines
            # print("Skipping blank line.")
            continue
        # This timeinfo could become a timedelta potentially..
        # although at present it still sorts correctly using the string.
        timeinfo, order_int, row_int, channels = getLinePatternInfo( line )
        if timeinfo and channels :
            #print("Storing key timeinfo:" + str( timeinfo ))
            #print("With channels:" + str( channels ))
            # Convert timeinfo back into a str?
            pattern_info_dict[ timeinfo ] = channels
            # print( "len(channels) was: " + str( len( channels ) ) )
            row_info_dict[ timeinfo ] = [order_int, row_int]
            # And so we don't append:
            continue
        # In theory there won't be anything of interest left!
        newlines.append( line )
        # Indeed if there's stuff other than whitespace left 
        # then there might have been a warning or error.?
    print( "getPatternInfo about to return.." )
    return newlines, pattern_info_dict, row_info_dict

# Example pos (21.886 seconds): Pos: 00:21.886
def getNoteNumber( note_str, last_note_number ):
    #print("getNoteNumber with str: " + str( note_str ))
    if note_str == "..." :
        return last_note_number
    if note_str == "===" :
        return last_note_number
    note_letter = note_str[0]
    # Start at zero for 'A'
    note_offset = ord( note_letter ) - 65
    sharp = int( note_str[1] == "#" )
    octave = int( note_str[2] )
    #print( "octave: " + str( octave ) )
    #print( "sharp: " + str( sharp ) )
    #print( "note_offset: " + str( note_offset ) )
    # This is completely wrong!
    #return 7*octave + note_offset + 0.5*sharp
    note_str_map=["A","A#","B","C","C#","D","D#","E","F","F#","G","G#" ]
    note_map = [0,0,1,2,2,3,3,4,5,5,6,6]
    #note_map = [0,0,1,1,2,3,3,4,4,5,5,6]
    # aka      [0,1,2,3,4,5,6,7,8,9,A,B] (where A=10, B=11)
    octave_base = octave * len( note_map )
    # Gets the index of the first occurange of that number
    # in the map, so that there's room for the sharps.
    note_base = note_map.index( note_offset )
    final_note = octave_base + note_base + sharp
    #print( "final_note: " + str( final_note ) )
    return final_note

def patternImportUpdateProgress( hinterup, progress, message=None, subprogress=None ):
    if subprogress is not None:
        hinterup.updateProgress( subprogress, )
    else :
        hinterup.updateProgress( progress, )
    if message is None:
        message = "Importing.."
    hinterup.updateLongProgress( progress, long_op_status=message )
    hou.ui.triggerUpdate()

def writeOutputsUpdateProgress( hinterup, progress, message=None, subprogress=None ):
    if subprogress is not None:
        hinterup.updateProgress( subprogress, )
    else :
        hinterup.updateProgress( progress, )
    if message is None:
        message = "Writing outputs.."
    hinterup.updateLongProgress( progress, long_op_status=message )
    hou.ui.triggerUpdate()
            
def incrementProgress( current_progress, relative_advance ) :
    if current_progress < 0.0 :
        current_progress = 0.0
    remaining_progress = 1.0 - current_progress
    #print( "remaining_progress: " + str( remaining_progress ) )
    advance = remaining_progress * relative_advance
    #print( "advance: " + str( advance ) )
    # clamp then!
    return min( 1.0, max( 0.0, current_progress + advance ) )

def makeKeyframe( secs, value, kf_function=None ):
    nkf = None
    if type( value ) == str :
        nkf = hou.StringKeyframe()
        nk.setExpression('"' + value + '"', hou.exprLanguage.Hscript )
    else :
        nkf = hou.Keyframe()
        nkf.setTime( secs )
        nkf.setValue( value )
        nkf.setSlopeAuto( True )
        nkf.setInSlopeAuto( True )
        nkf.setExpression( kf_function, hou.exprLanguage.Hscript )
    return nkf


def readPatternLog( ompt_node ):
    print("Read Pattern Log starting..")
    progress = 0.0
    all_chars = ""
    mod_log_file = getPatternLogOutputName( ompt_node ) #previously.. .evalParm("pattern_log_file")
    overwrite = bool( ompt_node.evalParm("overwrite") )
    
    with hou.InterruptableOperation( operation_name="Reading pattern log..", 
                                     long_operation_name="Importing Pattern Log..",
                                     open_interrupt_dialog=True ) as hinterup:
        
        kf_function = ompt_node.evalParm("keyframe_function")
        kf_time_offs = ompt_node.evalParm("keyframe_time_offset")
            
        print("Mod log file:" + str( mod_log_file ) )
        if not os.path.isfile( mod_log_file ):
            print("Pattern log file didn't exist!: " + str(plf) )
            return
        
        log_file = open( mod_log_file )
        progress = incrementProgress( progress, 0.01 )
        patternImportUpdateProgress( hinterup, progress, message="Reading pattern log file.." )
        lines = log_file.readlines()
        print("Got N lines: " + str( len( lines ) ) )
        progress = incrementProgress( progress, 0.09 )
        patternImportUpdateProgress( hinterup, progress, message="Parsing pattern log file.." )

        # print("lines: " + "".join(lines))
        # Method that strips the 'preamble' the info 
        # and copyright lines
        preamble_lines, remaining_lines = stripPreambleLines( lines )
        
        print("After stripPreamble there are: " + str( len( remaining_lines ) ) + " lines" )
        # Method that strips and extracts and returns the 
        # info in the info lines, such as 'Filename..." et al.
        minfo_lines, pattern_lines, info_dict = stripAndExtractModuleInfoLines( remaining_lines )
        
        for pat_line in pattern_lines:
            for char in pat_line :
                if char not in all_chars :
                    all_chars += char
        
        ompt_node.parm("preamble_lines").set("\n".join( preamble_lines + minfo_lines ) )
        ompt_node.parm("pattern_lines").set("\n".join( pattern_lines ) )
        
        # print( "Got info_dict: " + str( info_dict ) )
        if 'Channels' in info_dict :
            print("Info reckons there should be " 
                  + info_dict['Channels'] + " channels." )
        
        # Try/except ValueError if anything here.. I guess
        # we will just plough-ahead.
        nchans = int( info_dict['Channels'] )
        ompt_node.parm("num_channels").set(nchans)
        ompt_node.parm("channels").set(0)
        ompt_node.parm("channels").set(nchans)
        ompt_node.parm("generated_channels").set(0)
        ompt_node.parm("generated_channels").set(nchans)
        
        # NOTE: Later assumption of the same keys in both dicts here..
        stripped_lines, pattern_info_dict, row_info_dict = getPatternInfo( pattern_lines, nchans )
        
        # print("After pattern strip, expecing lines to be empty, lines is: " + "".join( lines ) )
        curr_line_keys = []
        order_keys = []
        row_keys = []
        note_keys = {}
        inst_keys = {}
        vol_keys = {}
        effec_keys = {}
        note_num_keys = {}
        note_hit_keys = {}
        note_time_keys = {}
        note_inst_keys = {}
        note_str_keys = {}
        # Pointless indices.. unless we need to reoprganise this later
        component_map = { 0 : note_keys, 
                          1 : inst_keys,
                          2 : vol_keys,
                          3 : effec_keys }
        # Needs to be dict per-channel:
        last_note_str = {}
        last_note_number = {}
        last_note_inst = {}
        last_note_hit = {}
        last_note_time = {}
        hit_decay = 0.75
        
        parse_progress_amount = 0.5
        pre_parse_progress = progress
        pinfo_keys = list( pattern_info_dict.keys() )
        # last_line = pinfo_keys.pop(-1)
        # print("About to enumerate pinfo_keys: " + str( pinfo_keys ) )
        for ix, key in enumerate( pinfo_keys ) :
            progress = ( ix / len( pattern_info_dict ) ) * parse_progress_amount + pre_parse_progress
            patternImportUpdateProgress( hinterup, 
                                         pre_parse_progress, 
                                         message="Reading pattern log file line: "\
                                         + str(ix+1) + " of " + str(len(pinfo_keys)),
                                         subprogress=progress )
            
            #print( "Progress: " + str( progress ) )
            #print( "Line: " + str( ix+1 ) + " of " + str( len( pattern_info_dict ) ) )
            # print( "pattern_info_dict key: " + str( key ) )
            strix = str( ix+1 )
            
            #print( "Pattern info key: " + str( key ) )
            val = pattern_info_dict[key]
            # ASSUMPTION these dicts have the same keys .. but safe for now..
            order_val, row_val = row_info_dict[key]
            
            ks_min_spl = key.split(":")
            if len( ks_min_spl ) != 2 :
                continue
                
            raw_secs = float( ks_min_spl[1] ) + 60 * float( ks_min_spl[0] )
            secs = raw_secs + kf_time_offs
            clk = hou.Keyframe()
            # print("Creating keyframes for pattern log line " + str( ix+1 ) + " with seconds: " + str( secs ) )
            print( "Secs: " + int(secs)//3 * "*" + ":" + str( secs ) )
            clk.setTime( secs )
            clk.setValue( float( ix+1 ) )
            clk.setSlopeAuto( True )
            clk.setInSlopeAuto( True )
            clk.setExpression( kf_function, hou.exprLanguage.Hscript )
            
            # This ordering is/was getting stuffed somehow!..
            # Ah.. turned out to be from not removing existing keyframes..
            # get rmoved when overwrite is true now
            # print( "Appending curr_line key: " + str( clk ) )
            curr_line_keys.append( clk )
            
            #print( "pattern_info_dict val: " + str( val ) )
            #print( "pattern_info_dict order_val: " + str( order_val ) )
            #print( "pattern_info_dict row_val: " + str( row_val ) )
            okf = makeKeyframe( secs, order_val, kf_function=kf_function )
            rkf = makeKeyframe( secs, row_val, kf_function=kf_function )
            order_keys.append( okf )
            row_keys.append( rkf )
            
            #print("key: " + str(key) + " val: " + str(val) )
            
            for chix, chan in enumerate( val ) :
                chrix = str( chix+1 )
                for indx, key_dict in component_map.items() :
                    # print("\n" + str( indx ) + " key_dict: " + str( key_dict ) )
                    note_str = chan[indx]
                    nk = hou.StringKeyframe()
                    nk.setTime( secs )
                    nk.setExpression('"' + note_str + '"', hou.exprLanguage.Hscript )
                    
                    if chrix in key_dict:
                        key_dict[chrix].append( nk )
                    else :
                        key_dict[chrix] = [ nk, ]
                    
                    if indx == 0 :
                        # Then we're on the Note column of a channel..
                        # collect some numeric keyframes too.
                        lnh = 0.0
                        lnt = -1.0 # Can mean 'no last hit time'
                        if note_str == "...":
                            if chrix in last_note_hit:
                                lnh = last_note_hit[chrix] * hit_decay
                                last_note_hit[chrix] = lnh
                            if chrix in last_note_time:
                                lnt = last_note_time[chrix]
                                #last_note_time[chrix] = lnh
                        else:
                            #if chix > 19 :
                            #    print( "Note hit: " + note_str + " on chrix:" + str( chrix ) )
                            lnh = 1.0
                            lnt = secs
                            last_note_hit[chrix] = lnh
                            last_note_time[chrix] = lnt
                        
                        # How's-about only making a new keyframe when there's a change? hmm
                        # as long as the row is included in that uniqueness-test then still
                        # all good with repeated notes..
                        nhk = makeKeyframe( secs, 
                                            value=float( lnh ), 
                                            kf_function=kf_function )
                        
                        if chrix in note_hit_keys:
                            note_hit_keys[chrix].append( nhk )
                        else :
                            note_hit_keys[chrix] = [ nhk, ]
                        
                        ntk = makeKeyframe( secs, 
                                             value=float( lnt ), 
                                             kf_function=kf_function )
                                             
                        if chrix in note_time_keys:
                            note_time_keys[chrix].append( ntk )
                        else :
                            note_time_keys[chrix] = [ ntk, ]
                            
                        lnn = 0.0
                        
                        if chrix in last_note_number :
                            lnn = last_note_number[chrix]
                                                    
                        cns = chan[indx]
                        note_number = getNoteNumber( cns, lnn )
                        if note_number != 0.0 :
                            last_note_number[chrix] = note_number
                        
                        #Note number Keyframes
                        fnk = hou.Keyframe()
                        fnk.setTime( secs )
                        fnk.setValue( float( note_number ) )
                        fnk.setSlopeAuto(True)
                        fnk.setInSlopeAuto(True)
                        fnk.setExpression( kf_function, hou.exprLanguage.Hscript)
                        
                        if chrix in note_num_keys:
                            note_num_keys[chrix].append( fnk )
                        else :
                            note_num_keys[chrix] = [ fnk, ]
                        
                        # Now do note str:
                        lns = "..."
                        if chrix in last_note_str:
                            lns = last_note_str[chrix]
                            
                        note_str = lns
                        
                        if cns != "" and cns != "...":
                            note_str = cns
                            
                        if note_str != "" and note_str != "...":
                            last_note_str[chrix] = cns
                        
                        nsk = hou.StringKeyframe()
                        nsk.setTime( secs )
                        nsk.setExpression('"' + chan[indx] + '"', hou.exprLanguage.Hscript )

                        if chrix in note_str_keys:
                            note_str_keys[chrix].append( nsk )
                        else :
                            note_str_keys[chrix] = [ nsk, ]
                        
                    elif indx == 1 :
                        # inst
                        inst_hex = chan[indx]
                        if inst_hex != "..":
                            # print("Inst hex:" + inst_hex)
                            note_inst = int( inst_hex, 16 )
                            # print("Note int: " + str( note_inst ))
                            # Are we meant to be checking if we've changed?
                            last_note_inst[chrix] = note_inst
                            ink = hou.Keyframe()
                            ink.setTime( secs )
                            ink.setValue( float( note_inst ) )
                            ink.setSlopeAuto(True)
                            ink.setInSlopeAuto(True)
                            ink.setExpression( kf_function, hou.exprLanguage.Hscript)
                            if chrix in note_inst_keys:
                                note_inst_keys[chrix].append( ink )
                            else :
                                note_inst_keys[chrix] = [ ink, ]
        
        # 0.8 to 1.0ish in 13 steps or so for the moment..
        post_parse_steps = 13
        
        progress = incrementProgress( progress, 1.0/post_parse_steps )
        patternImportUpdateProgress( hinterup, progress, message="Making current line/order/row keyframes.." )
        if curr_line_keys:
            if ompt_node.parm( "current_line" ).keyframes():
                ompt_node.parm( "current_line" ).deleteAllKeyframes()
            ompt_node.parm( "current_line" ).setKeyframes( curr_line_keys )
        
        if order_keys:
            # if overwrite:
            if ompt_node.parm( "current_order_num" ).keyframes():
                ompt_node.parm( "current_order_num" ).deleteAllKeyframes()
            ompt_node.parm( "current_order_num" ).setKeyframes( order_keys )
            
        if row_keys:
            # if overwrite:
            if ompt_node.parm( "current_row_num" ).keyframes():
                ompt_node.parm( "current_row_num" ).deleteAllKeyframes()
            ompt_node.parm( "current_row_num" ).setKeyframes( row_keys )
        
        progress = incrementProgress( progress, 1.0/post_parse_steps )
        patternImportUpdateProgress( hinterup, progress, message="Making note keyframes.." )
        for chrix in note_keys.keys() :
            ompt_node.parm( "note" + chrix ).setKeyframes( note_keys[chrix] )
            
        progress = incrementProgress( progress, 1.0/post_parse_steps )
        patternImportUpdateProgress( hinterup, progress, message="Making instrument keyframes.." )
        for chrix in inst_keys.keys() :
            ompt_node.parm( "instrument" + chrix ).setKeyframes( inst_keys[chrix] )

        progress = incrementProgress( progress, 1.0/post_parse_steps )
        patternImportUpdateProgress( hinterup, progress, message="Making volume keyframes.." )
        for chrix in inst_keys.keys() :
            ompt_node.parm( "volume" + chrix ).setKeyframes( vol_keys[chrix] )

        progress = incrementProgress( progress, 1.0/post_parse_steps )
        patternImportUpdateProgress( hinterup, progress, message="Making effect keyframes.." )
        for chrix in inst_keys.keys() :
            ompt_node.parm( "effect" + chrix ).setKeyframes( effec_keys[chrix] )

        progress = incrementProgress( progress, 1.0/post_parse_steps )
        patternImportUpdateProgress( hinterup, progress, message="Making note number keyframes.." )
        for chrix in note_num_keys.keys() :
            ompt_node.parm( "note_number" + chrix ).setKeyframes( note_num_keys[chrix] )

        progress = incrementProgress( progress, 1.0/post_parse_steps )
        patternImportUpdateProgress( hinterup, progress, message="Making note hit keyframes.." )
        for chrix in note_hit_keys.keys() :
            ompt_node.parm( "note_hit" + chrix ).setKeyframes( note_hit_keys[chrix] )
            
        progress = incrementProgress( progress, 1.0/post_parse_steps )
        patternImportUpdateProgress( hinterup, progress, message="Making note hit time keyframes.." )
        for chrix in note_time_keys.keys() :
            ompt_node.parm( "note_time" + chrix ).setKeyframes( note_time_keys[chrix] )
        
        progress = incrementProgress( progress, 1.0/post_parse_steps )
        patternImportUpdateProgress( hinterup, progress, message="Making note str keyframes.." )
        for chrix in note_str_keys.keys() :
            ompt_node.parm( "note_str" + chrix ).setKeyframes( note_str_keys[chrix] )

        progress = incrementProgress( progress, 1.0/post_parse_steps )
        patternImportUpdateProgress( hinterup, progress, message="Making note inst keyframes.." )
        for chrix in note_inst_keys.keys() :
            ompt_node.parm( "note_inst" + chrix ).setKeyframes( note_inst_keys[chrix] )
            
        progress = incrementProgress( progress, 1.0/post_parse_steps )
        patternImportUpdateProgress( hinterup, progress, message="Setting all chars.." )
        ompt_node.parm("all_chars").set( all_chars )
        progress = 1.0
        patternImportUpdateProgress( hinterup, progress, message="All Done!",subprogress=progress )

def getExtractedLinesBack( ompt_node ) :
    lines_back = int( ompt_node.evalParm("extract_lines_back") )
    lines = ompt_node.evalParm("pattern_lines")
    curr_line = int( ompt_node.evalParm("current_line") )
    lines_spl = lines.split("\n")
    #print( "num_lines (total): " + str( len( lines_spl ) ) )
    start_line = max(0, curr_line - lines_back)
    end_line = min( len( lines_spl )-1, curr_line )
    #print( "start_line: " + str( start_line ) )
    #print( "end_line: " + str( end_line ) )    
    return "\n".join( lines_spl[ start_line:end_line ] )
