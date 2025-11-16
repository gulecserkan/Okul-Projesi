import os


def _read_version_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def get_version(default="dev"):
    """
    Uygulama sürümünü VERSION dosyasından okur.
    Paketlenmiş kurulumda /opt/kutuphane-desktop/VERSION içinde bulunur.
    Geliştirme sırasında proje kökündeki VERSION dosyasını okur.
    """
    here = os.path.abspath(os.path.dirname(__file__))
    candidates = [
        os.path.join(here, "..", "VERSION"),
        os.path.join(here, "..", "..", "VERSION"),
    ]
    for path in candidates:
        version = _read_version_file(path)
        if version:
            return version
    return default
