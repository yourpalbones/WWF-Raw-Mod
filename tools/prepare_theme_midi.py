"""Prepare supplied MIDI for WrestleEdit without changing melodic note timing.

Requires mido. Channel 10 percussion is omitted; metadata, tempo, controllers,
programs, melodic notes and original track duration remain intact. The native
editor replaces MIDI program assignments with its selected game sample.
Optional unison merging combines equal-pitch notes with the same onset, retaining
their longest held duration and maximum velocity.
"""
import argparse,hashlib,json
from pathlib import Path
from collections import Counter
import mido

def paired_notes(track):
    active={};rows=[];tick=0
    for i,message in enumerate(track):
        tick+=message.time
        if message.type=='note_on'and message.velocity:
            active.setdefault((message.channel,message.note),[]).append((i,tick,message.velocity))
        elif message.type=='note_off'or message.type=='note_on'and not message.velocity:
            key=(message.channel,message.note);pending=active.get(key,[])
            if pending:
                on,start,velocity=pending.pop(0)
                rows.append({'on':on,'off':i,'start':start,'end':tick,'channel':key[0],'pitch':key[1],'velocity':velocity})
    return rows

def combine_unisons(track):
    groups={};removed=set();velocities={};combined=0
    for row in paired_notes(track):groups.setdefault((row['channel'],row['pitch'],row['start']),[]).append(row)
    for rows in groups.values():
        if len(rows)<2:continue
        keep=max(rows,key=lambda n:n['end']);velocities[keep['on']]=max(n['velocity']for n in rows)
        for row in rows:
            if row is not keep:removed.update([row['on'],row['off']]);combined+=1
    output=mido.MidiTrack();pending=0
    for i,message in enumerate(track):
        pending+=message.time
        if i in removed:continue
        output.append(message.copy(time=pending,**({'velocity':velocities[i]}if i in velocities else{})));pending=0
    assert not pending
    return output,combined

def coverage(file):
    result={}
    for i,track in enumerate(file.tracks):
        for row in paired_notes(track):
            key=(i,row['channel'],row['pitch'],row['start']);prior=result.get(key,(0,0))
            result[key]=(max(prior[0],row['end']),max(prior[1],row['velocity']))
    return result

def prepare(source,destination,merge_unisons=False):
    midi=mido.MidiFile(source);result=mido.MidiFile(type=midi.type,ticks_per_beat=midi.ticks_per_beat)
    removed=Counter();notes=Counter();drum_notes=0
    for track in midi.tracks:
        output=mido.MidiTrack();pending=0
        for message in track:
            pending+=message.time
            if getattr(message,'channel',None)==9:
                removed[message.type]+=1
                if message.type=='note_on'and message.velocity:drum_notes+=1
                continue
            output.append(message.copy(time=pending));pending=0
            if message.type=='note_on'and message.velocity:notes[message.channel]+=1
        if pending:
            # Normally end_of_track carries the delay. Preserve duration even
            # in an unusual track ending immediately after a drum event.
            output.append(mido.MetaMessage('end_of_track',time=pending))
        result.tracks.append(output)
    melodic_original=result;combined=0
    if merge_unisons:
        result=mido.MidiFile(type=midi.type,ticks_per_beat=midi.ticks_per_beat)
        for track in melodic_original.tracks:
            output,count=combine_unisons(track);result.tracks.append(output);combined+=count
        assert coverage(result)==coverage(melodic_original),'Distinct notes or sustain coverage changed'
    destination.parent.mkdir(parents=True,exist_ok=True);result.save(destination)
    def melodic_events(file):
        events=[]
        for i,track in enumerate(file.tracks):
            tick=0
            for message in track:
                tick+=message.time
                if getattr(message,'channel',None)!=9:
                    events.append((i,tick,message.copy(time=0)))
        return events
    if not merge_unisons:assert melodic_events(midi)==melodic_events(mido.MidiFile(destination))
    else:
        def metadata(file):
            return[(i,tick,m)for i,tick,m in melodic_events(file)if m.type not in {'note_on','note_off'}]
        assert metadata(midi)==metadata(result),'Tempo, controllers or credits changed'
    assert abs(midi.length-result.length)<1e-8
    return {'source':source.name,'prepared':destination.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'prepared_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
            'removed_percussion_events':dict(removed),'removed_percussion_notes':drum_notes,
            'original_melodic_notes':sum(notes.values()),'retained_melodic_notes':sum(notes.values())-combined,'melodic_channels_before_merge':dict(notes),
            'redundant_simultaneous_notes_combined':combined,
            'seconds':result.length,'melodic_events_and_metadata_tick_exact':not combined,
            'distinct_note_pitch_onset_sustain_and_velocity_preserved':True,'metadata_tick_exact':True,
            'transpose_semitones':0,'pitch_bends_removed':0}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path);p.add_argument('--report',type=Path,required=True);p.add_argument('--merge-unisons',action='store_true');a=p.parse_args()
    report=prepare(a.source,a.destination,a.merge_unisons);a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
