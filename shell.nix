# Usamos o pkgs padrão fornecido pelo ambiente
{ pkgs ? import <nixpkgs> {} }:

# Criamos um 'let' block para definir uma variável local
let
  # Esta é a nossa instância de pacotes separada e configurada para permitir software "não-livre"
  unfreePkgs = import <nixpkgs> { config.allowUnfree = true; };
in
pkgs.mkShell {
  buildInputs = with pkgs; [
    # --- Pacotes Livres (usando o 'pkgs' padrão) ---
    python311Full
    unixODBC
    gcc
    python311Packages.pandas
    python311Packages.pyodbc
    python311Packages.beautifulsoup4
    python311Packages.lxml
    python311Packages.openpyxl
    python311Packages.ipython

    # --- Pacote Não-Livre (usando nossa instância 'unfreePkgs' e o sub-atributo 'unfree') ---
    (unfreePkgs.unfree.msodbcsql17.override {accept_eula = true;})
  ];

  # A configuração do ODBC também precisa ser atualizada para usar a instância e o caminho corretos
  shellHook = ''
    export ODBCSYSINI=${pkgs.stdenv.mkDerivation {
      name = "odbc-config";
      src = ./odbc.ini;
      # O ambiente de build da configuração precisa do driver
      nativeBuildInputs = [ (unfreePkgs.unfree.msodbcsql17.override {accept_eula = true;}) ];
      installPhase = ''
        mkdir -p $out/etc
        cp $src $out/etc/odbc.ini
        # Geramos o odbcinst.ini usando o caminho do driver da instância 'unfreePkgs'
        echo "[ODBC Driver 17 for SQL Server]" > $out/etc/odbcinst.ini
        echo "Description=Microsoft ODBC Driver 17 for SQL Server" >> $out/etc/odbcinst.ini
        echo "Driver=$(find ${(unfreePkgs.unfree.msodbcsql17.override {accept_eula = true;})} -name libmsodbcsql-17.so.*)" >> $out/etc/odbcinst.ini
        echo "UsageCount=1" >> $out/etc/odbcinst.ini
      '';
    }}/etc
  '';
}
