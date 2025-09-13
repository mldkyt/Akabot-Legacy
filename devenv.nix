{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

{
  dotenv.enable = true;

  packages = [
    pkgs.watchexec
    pkgs.jetbrains.pycharm-community
  ];

  languages.python = {
    enable = true;
    version = "3.10";
    venv.enable = true;
    venv.requirements = ''
      certifi
      emoji
      py-cord
      pymongo
      python-dotenv
      python-gitlab
      pytimeparse
      requests
      markovify
      python-i18n
    '';
  };

  services.mongodb = {
    enable = true;
    initDatabaseUsername = "lunya";
    initDatabasePassword = "changeme";
  };

  processes = {
    akabot.exec = "watchexec -r -e py python3 main.py";
    pycharm.exec = "pycharm-community .";
  };

  enterShell = ''
    # Create a symlink to the Python virtual environment for IDE compatibility
    if [ ! -L "$DEVENV_ROOT/venv" ]; then
        ln -s "$DEVENV_STATE/venv/" "$DEVENV_ROOT/venv"
    fi
  '';

}
