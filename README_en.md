Music Tagger is a Windows application written in Python and designed to automatically or manually change the metadata of mp3 audio files.

**Features:**
-  opening a folder with mp3 files or a single file 
-  automatically searching for the artist, track name, and album name, as well as the release year 
-  loading the cover image 
-  creating a backup before making changes 
-  manually editing the metadata of a single track 
-  viewing detailed information about the file
-  supports mp3/flac/m4a/aac/ogg/wav

Please note that the search is performed if the file has a name of the form *Fried_By_Fluoride_-The_Love_I_Lost_78276350* - the artist and song title are read. Excessive characters are automatically removed (except for duplicate markings, such as (2), which must be removed manually).

 **Important note:**
Music Tagger uses external services to search for metadata and artwork. 
In some regions, access to these services may be restricted.  If the program shows network errors, check your internet connection and use workarounds if necessary (VPN or, for example, zapret). If you are using zapret, then insert the following domains in list-general.txt:

> `musicbrainz.org`  
> `coverartarchive.org`  
> `archive.org`  
> `s3.us.archive.org`