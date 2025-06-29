{ pkgs ? import <nixpkgs> {} }:

let
  # Permite pacotes não-livres
  unfreePkgs = import <nixpkgs> { config.allowUnfree = true; };
in

pkgs.mkShell {
  buildInputs = with pkgs; [
    # --- Pacotes livres ---
    python311Full
    unixODBC
    gcc
    python311Packages.pandas
    python311Packages.pyodbc
    python311Packages.beautifulsoup4
    python311Packages.lxml
    python311Packages.openpyxl
    python311Packages.ipython

    # --- Driver Microsoft ODBC 17 (não-livre) ---
    unfreePkgs.unixODBCDrivers.msodbcsql17
  ];

  shellHook = ''
    export ODBCSYSINI=${
      pkgs.stdenv.mkDerivation {
        name = "odbc-config";
        src = ./odbc.ini;

        # Impede que o Nix tente desempacotar o odbc.ini como se fosse um tarball
        unpackPhase = "true";

        nativeBuildInputs = [
          unfreePkgs.unixODBCDrivers.msodbcsql17
        ];

        installPhase = ''
          mkdir -p $out/etc
          cp $src $out/etc/odbc.ini

          # Geramos o odbcinst.ini apontando para o driver instalado
          echo "[ODBC Driver 17 for SQL Server]" > $out/etc/odbcinst.ini
          echo "Description=Microsoft ODBC Driver 17 for SQL Server" >> $out/etc/odbcinst.ini
          echo "Driver=$(find ${unfreePkgs.unixODBCDrivers.msodbcsql17} -name libmsodbcsql-17.so.*)" >> $out/etc/odbcinst.ini
          echo "UsageCount=1" >> $out/etc/odbcinst.ini
        '';
      }
    }/etc
  '';
}
