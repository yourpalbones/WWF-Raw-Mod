#include <stdio.h>
#include <stdlib.h>
#ifndef INLINE
#define INLINE inline
#endif
#include <libchdr/chd.h>
int main(int argc,char**argv){if(argc!=3){fprintf(stderr,"usage: extract INPUT.chd OUTPUT.raw\n");return 1;}chd_file*c;chd_error e=chd_open(argv[1],CHD_OPEN_READ,NULL,&c);if(e){fprintf(stderr,"open %d\n",e);return 1;}const chd_header*h=chd_get_header(c);printf("hunks %u bytes %u logical %llu unit %u\n",h->totalhunks,h->hunkbytes,(unsigned long long)h->logicalbytes,h->unitbytes);char meta[1024];for(unsigned i=0;chd_get_metadata(c,CDROM_TRACK_METADATA2_TAG,i,meta,sizeof(meta),NULL,NULL,NULL)==0;i++)printf("%s\n",meta);FILE*f=fopen(argv[2],"wb");if(!f){perror("output");chd_close(c);return 1;}void*b=malloc(h->hunkbytes);if(!b){fclose(f);chd_close(c);return 1;}unsigned long long remaining=h->logicalbytes;for(unsigned i=0;i<h->totalhunks;i++){e=chd_read(c,i,b);if(e){fprintf(stderr,"hunk %u error %d\n",i,e);return 2;}size_t n=remaining<h->hunkbytes?remaining:h->hunkbytes;if(fwrite(b,1,n,f)!=n){perror("write");return 3;}remaining-=n;}free(b);if(fclose(f)){perror("close");return 3;}chd_close(c);return 0;}
