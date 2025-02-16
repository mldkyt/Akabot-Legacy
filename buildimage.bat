docker build -t akabot:latest .
docker tag akabot:latest code.mldchan.dev/mld/akabot:latest
docker tag akabot:latest codeberg.org/mldchan/akabot:latest
docker push code.mldchan.dev/mld/akabot:latest
docker push codeberg.org/mldchan/akabot:latest