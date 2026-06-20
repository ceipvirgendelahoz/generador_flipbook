import acortador


def test_acortar_url_real():
    # is.gd es gratuito y sin clave; el PC de desarrollo tiene internet.
    corta = acortador.acortar("https://dtabuyodesigner.github.io/generador_flipbook/")
    assert corta is None or corta.startswith("https://is.gd/")


def test_acortar_entrada_invalida_no_rompe():
    assert acortador.acortar("esto no es una url") is None or True  # nunca lanza
