docker build -t akabot:latest .
docker tag akabot:latest git.lunya.pet/Lunya/akabot:latest
docker tag akabot:latest codeberg.org/LunyaUwU/akabot:latest
docker push git.lunya.pet/Lunya/akabot:latest
docker push codeberg.org/LunyaUwU/akabot:latest