docker build -t akabot:latest-msg .
docker tag akabot:latest code.mldchan.dev/mld/akabot:latest-msg
docker tag akabot:latest codeberg.org/mldchan/akabot:latest-msg
docker push code.mldchan.dev/mld/akabot:latest-msg
docker push codeberg.org/mldchan/akabot:latest-msg