{
  description = "Development environment for Arca Flow";

  inputs = {
    nix-aerie.url = "github:eth-library/nix-aerie";
    nixpkgs.follows = "nix-aerie/nixpkgs";
  };

  outputs = { self, nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            pkgs.python314
            pkgs.uv
            pkgs.just
          ];
          # Required for pip-installed packages with C++ extensions (e.g., grpcio)
          LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
            pkgs.stdenv.cc.cc.lib
          ];
        };
      });
    };
}
