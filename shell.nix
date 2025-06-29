{ pkgs ? import <nixpkgs> {} }:

let
  # permite software não-livre
  unfreePkgs = import <nixpkgs> { config.allowUnfree = true; };
in

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python & libs
    python311Full
    unixODBC
    gcc
    python311Packages.pandas
    python311Packages.pyodbc
    python311Packages.beautifulsoup4
    python311Packages.lxml
    python311Packages.openpyxl
    python311Packages.ipython

    # Driver Microsoft ODBC 17 (não-livre)
    unfreePkgs.unixODBCDrivers.msodbcsql17
  ];

  shellHook = ''
    # cria um mini-derivativo que exponha o odbc.ini e gere o odbcinst.ini
    export ODBCSYSINI=${
      pkgs.stdenv.mkDerivation {
        name = "odbc-config";
        src = ./odbc.ini;
        unpackPhase = "true";
        nativeBuildInputs = [ unfreePkgs.unixODBCDrivers.msodbcsql17 ];
        installPhase = ''
          mkdir -p $out/etc
          cp $src $out/etc/odbc.ini

          # Gera odbcinst.ini apontando para o .so real
          echo "[ODBC Driver 17 for SQL Server]" > $out/etc/odbcinst.ini
          echo "Description=Microsoft ODBC Driver 17 for SQL Server" >> $out/etc/odbcinst.ini

          # procura o .so dentro do pacote msodbcsql17 e pega o primeiro
          driver=$(find ${unfreePkgs.unixODBCDrivers.msodbcsql17} \
                   -type f -path "*/lib*/libmsodbcsql-17*.so*" | head -n1)
          if [ -z "$driver" ]; then
            echo "ERRO: não achei o libmsodbcsql-17.so em ${unfreePkgs.unixODBCDrivers.msodbcsql17}" >&2
            exit 1
          fi

          echo "Driver=$driver" >> $out/etc/odbcinst.ini
          echo "UsageCount=1" >> $out/etc/odbcinst.ini
        '';
      }
    }/etc

    # exporta também ODBCINI e ODBCINSTINI para o Node/Python herdarem
    export ODBCINI="$ODBCSYSINI/odbc.ini"
    export ODBCINSTINI="$ODBCSYSINI/odbcinst.ini"
  '';
}
