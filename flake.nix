{
  description = "PDF OCR with Gemini API - GUI and API Services";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;
        pythonPackages = python.pkgs;
      in
      {
        # Define the default package (Python application)
        packages.default = pythonPackages.buildPythonApplication {
          pname = "pdf-ocr-gemini";
          version = "0.1.0";
          src = ./.;

          propagatedBuildInputs = with pythonPackages; [
            fastapi
            google-generativeai
            markdown
            tqdm
            pdf2image
            pillow
            streamlit
            uvicorn
            python-multipart
            pypdf2
          ];


          meta = with pkgs.lib; {
            description = "PDF OCR with Gemini API";
            license = licenses.mit;
            maintainers = with maintainers; [ your-name ];
          };
        };

        # Development shell
        devShell = pkgs.mkShell {
          buildInputs = with pythonPackages; [
            fastapi
            google-generativeai
            markdown
            tqdm
            pdf2image
            pillow
            streamlit
            uvicorn
            python-multipart
           pypdf2
          ];
        };
      }
    ) // {
      # Expose NixOS modules for the GUI and API services
      nixosModules = {
        guiService = { config, pkgs, ... }: {
          systemd.services.pdf-ocr-gui = {
            description = "PDF OCR GUI Service";
            after = [ "network.target" ];
            wantedBy = [ "multi-user.target" ];

            serviceConfig = {
              ExecStart = "${pkgs.python312Packages.streamlit}/bin/streamlit run ${self}/google_ocr_gui.py --server.port=8501";
              Restart = "always";
              User = "nobody";
              WorkingDirectory = "${self}";
            };
          };
        };

        apiService = { config, pkgs, ... }: {
          systemd.services.pdf-ocr-api = {
            description = "PDF OCR API Service";
            after = [ "network.target" ];
            wantedBy = [ "multi-user.target" ];

            serviceConfig = {
              ExecStart = "${pkgs.python312Packages.uvicorn}/bin/uvicorn google_ocr_api:app --host 0.0.0.0 --port 8000";
              Restart = "always";
              User = "nobody";
              WorkingDirectory = "${self}";
            };
          };
        };
      };
    };
}