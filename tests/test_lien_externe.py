"""Une adresse venue du dehors n'est pas une adresse.

CE QUI ÉTAIT OUVERT, ET QUE J'AVAIS OUVERT MOI-MÊME. Depuis que la veille lit
trente-six flux extérieurs, chaque élément apporte une adresse écrite par un
tiers, et elle rejoignait deux affichages — la page publique et la console
d'administration — simplement ÉCHAPPÉE. Or échapper protège du BALISAGE, pas du
SCHÉMA : `javascript:alert(1)` dans un href s'exécute au clic, guillemets
neutralisés ou non.

La maison tenait déjà cette garde dans la page de jurisprudence — « on n'ouvre
que http et https » — avec un essai qui éprouve `javascript:` et
`JaVaScRiPt:`. Elle n'avait été appliquée nulle part ailleurs.

LE SECOND RISQUE N'EST PAS LE MÊME. Une adresse que le SERVEUR va chercher
désigne ce que le serveur peut joindre : le service de métadonnées de
l'hébergeur, la boucle locale, le réseau privé. La requête part de l'intérieur,
aucun pare-feu ne la voit passer.
"""
import os
import sys

import pytest

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ICI)

import automation                                                   # noqa: E402
import lien_externe as L                                            # noqa: E402
import veille_facettes as vf                                        # noqa: E402


# ── 1. Ce qui s'exécute au clic ────────────────────────────────────────────

@pytest.mark.parametrize("mauvais", [
    "javascript:alert(1)", "JaVaScRiPt:alert(1)", "  javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>", "vbscript:msgbox(1)",
    "file:///etc/passwd", "//exemple.fr/a",
])
def test_un_schema_qui_s_execute_n_est_jamais_affichable(mauvais):
    assert L.sur(mauvais) == ""


@pytest.mark.parametrize("bon", ["https://exemple.fr/a", "http://exemple.fr",
                                 "HTTPS://EXEMPLE.FR/A"])
def test_une_adresse_ordinaire_passe(bon):
    """Le pendant : une garde qui refuserait tout serait verte sur la règle
    précédente et rendrait la veille inutilisable."""
    assert L.sur(bon) == bon.strip()


def test_la_liste_est_BLANCHE_et_non_noire():
    """Une liste noire de « javascript: » oublierait `data:`, `vbscript:`, et
    le schéma que le prochain navigateur inventera."""
    assert L.sur("schemeinconnu://exemple.fr/a") == ""


# ── 2. Ce que le serveur ne doit pas aller chercher ────────────────────────

@pytest.mark.parametrize("interne", [
    "http://169.254.169.254/latest/meta-data/",
    "http://metadata.google.internal/computeMetadata/v1/",
    "https://127.0.0.1/admin", "https://localhost/admin",
    "https://10.0.0.5/", "https://192.168.1.1/", "https://172.16.0.1/",
    "https://[::1]/", "https://[fe80::1]/", "https://0.0.0.0/",
    "https://base.internal/",
    # LE CAS QUE SEULE LA LISTE DE MÉTADONNÉES COUVRE. « metadata » tout court
    # n'est ni une adresse IP — donc aucune règle de réseau ne le voit — ni un
    # nom en « .internal ». Sans ce cas, une mutation supprimant la liste
    # survivait : la règle éprouvait des hôtes déjà protégés deux fois.
    "http://metadata/computeMetadata/v1/",
])
def test_le_serveur_ne_va_pas_chercher_chez_lui(interne):
    assert L.joignable(interne) is False


def test_une_adresse_ipv6_entre_crochets_est_bien_lue():
    """LE DÉFAUT DE MA PREMIÈRE GARDE. Une adresse IPv6 s'écrit entre crochets
    et ses deux-points font partie de l'adresse : une expression qui découpait
    au premier « : » rendait « [ » comme hôte — que `ip_address` refuse, et que
    la garde laissait donc passer pour un nom de domaine. `https://[::1]/`
    franchissait le contrôle : la boucle locale, dans l'autre notation."""
    assert L.hote("https://[::1]/x") == "::1"
    assert L.joignable("https://[::1]/x") is False


def test_un_nom_public_reste_joignable():
    assert L.joignable("https://www.cert.ssi.gouv.fr/avis/feed/") is True


def test_les_identifiants_dans_l_adresse_ne_masquent_pas_l_hote():
    """« https://exemple.fr@127.0.0.1/ » désigne 127.0.0.1, pas exemple.fr.
    Une garde qui lirait le début de la chaîne se ferait tromper par la partie
    utilisateur."""
    assert L.hote("https://exemple.fr@127.0.0.1/x") == "127.0.0.1"
    assert L.joignable("https://exemple.fr@127.0.0.1/x") is False


def test_le_module_dit_la_limite_qu_il_ne_couvre_pas():
    """Aucune résolution de nom : un domaine public pointant vers une adresse
    privée franchit cette garde. Le taire donnerait une confiance que rien ne
    soutient."""
    assert "résolution de nom" in L.glossaire()["limite"]


# ── 3. La garde est posée AU SERVEUR, pas dans la page ────────────────────

def test_un_lien_de_flux_hostile_ne_sort_pas_de_l_api():
    """La garde tient côté serveur : elle couvre la page publique ET la console
    d'administration d'un seul coup — et couvrira le troisième affichage."""
    items = vf.enrichir([{"title": "T", "resume": "", "source": "dcd",
                          "link": "javascript:alert(1)", "published": 0,
                          "guid": "g"}])
    assert items[0]["link"] == ""


def test_un_lien_de_flux_ordinaire_traverse():
    items = vf.enrichir([{"title": "T", "resume": "", "source": "dcd",
                          "link": "https://exemple.fr/a", "published": 0,
                          "guid": "g"}])
    assert items[0]["link"] == "https://exemple.fr/a"


def test_le_serveur_refuse_de_telecharger_une_adresse_interne():
    """Le téléchargement du texte intégral suit une adresse VENUE DU FLUX."""
    appels = []

    def _fetch(url, timeout=12):
        appels.append(url)
        return "du texte"

    assert automation._fetch_bulletin_text(
        "http://169.254.169.254/latest/meta-data/", _fetch) is None
    assert appels == [], "le serveur a interrogé l'adresse interne"


def test_le_serveur_telecharge_une_adresse_publique():
    """Le pendant : une garde qui refuserait tout ferait passer la règle
    précédente sans rien protéger."""
    appels = []

    def _fetch(url, timeout=12):
        appels.append(url)
        return "<html><body>du texte de bulletin</body></html>"

    automation._fetch_bulletin_text("https://www.cert.ssi.gouv.fr/avis/AV-1/",
                                    _fetch)
    assert appels, "une adresse publique doit être suivie"


# ── 4. Le nom de colonne qui finissait dans le SQL ────────────────────────

def test_seules_les_colonnes_prevues_sont_interrogeables():
    """Un nom de colonne ne peut pas être passé en paramètre : il finit dans la
    chaîne SQL. La question n'est pas comment l'échapper, c'est d'où il vient —
    et ce chemin lit la table des COMPTES."""
    import auth
    magasin = auth._PgStore.__new__(auth._PgStore)
    with pytest.raises(ValueError):
        magasin.get_by("email; DROP TABLE users --", "x")
    with pytest.raises(ValueError):
        magasin.get_by("password_hash", "x")
    assert "reset_token" in auth._PgStore._CHAMPS_CHERCHABLES
