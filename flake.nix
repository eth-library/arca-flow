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
      devShells = forAllSystems (pkgs:
        let
          # Package groups
          basePackages = [
            pkgs.python312
            pkgs.uv
            pkgs.just
          ];
          k8sPackages = [
            pkgs.kubectl
            pkgs.kubernetes-helm
          ];

          # Helper to create shells with common settings
          mkDevShell = packages: pkgs.mkShell {
            inherit packages;
            # Required for pip-installed packages with C++ extensions (e.g., grpcio)
            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
              pkgs.stdenv.cc.cc.lib
            ];
          };

        in {
          # Default: Python + uv + kubectl + helm
          default = mkDevShell (basePackages ++ k8sPackages);

          # Minimal: Python + uv (for running pipeline and tests)
          minimal = mkDevShell basePackages;
        }
      );
    };
}
