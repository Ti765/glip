{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python311Full
    pkgs.python311Packages.pip
    pkgs.python311Packages.pandas
    pkgs.python311Packages.pyodbc
    pkgs.python311Packages.beautifulsoup4
    pkgs.python311Packages.lxml
    pkgs.python311Packages.openpyxl
    pkgs.gcc            # para trazer libstdc++.so.6
  ];
}
