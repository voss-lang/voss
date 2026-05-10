class Voss < Formula
  desc "Voss compiler and agent CLI"
  homepage "https://github.com/bm9797/Voss"
  version "0.1.0"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/bm9797/Voss/releases/download/v#{version}/voss-cli-aarch64-apple-darwin.tar.xz"
      sha256 "<filled-by-cargo-dist>"
    end

    on_intel do
      url "https://github.com/bm9797/Voss/releases/download/v#{version}/voss-cli-x86_64-apple-darwin.tar.xz"
      sha256 "<filled-by-cargo-dist>"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/bm9797/Voss/releases/download/v#{version}/voss-cli-aarch64-unknown-linux-gnu.tar.xz"
      sha256 "<filled-by-cargo-dist>"
    end

    on_intel do
      url "https://github.com/bm9797/Voss/releases/download/v#{version}/voss-cli-x86_64-unknown-linux-gnu.tar.xz"
      sha256 "<filled-by-cargo-dist>"
    end
  end

  def install
    bin.install "voss-cli"
    bin.install_symlink bin/"voss-cli" => "voss"
  end

  test do
    assert_match "voss", shell_output("#{bin}/voss-cli --version")
  end
end
