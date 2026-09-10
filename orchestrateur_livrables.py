# -*- coding: utf-8 -*-
"""Un orchestrateur agentique pour la rédaction de livrables, et des agents
réutilisables PAR SUJET — IEC 62443, NIS2, un lot de centre de données…

CE QUE CETTE COUCHE APPORTE, ET CE QU'ELLE N'INVENTE PAS. La génération ancrée
sur la base existait déjà : recherche large, re-classement par un juge,
aiguillage famille → discipline → stade, rédaction. Cette couche NE refait rien
de tout cela. Elle NOMME une configuration par sujet — un « agent » —, la
RÉUTILISE d'une demande à l'autre (fluidité), et offre un LEVIER DE RAPIDITÉ
explicite.

L'AGENT EST GÉNÉRAL, PAS RÉSERVÉ AUX CENTRES DE DONNÉES. Il route chaque type
de livrable vers SES thèmes de la base : une synthèse IEC 62443 vers le
référentiel « IEC 62443 », un lot de data center vers la famille « Centres de
données » et le sous-dossier de son stade. Le sujet décide, pas le module.

LE LEVIER DE RAPIDITÉ, DÉCLARÉ. Le mode rapide SAUTE le re-classement par le
juge — un appel modèle de moins, une réponse plus prompte — au prix, dit en
toutes lettres, d'un rappel un peu moindre. Un compromis nommé n'est pas un
compromis caché.

L'ORCHESTRATEUR NE RÉDIGE PAS. Il route, mémoïse le plan, et le rend.
L'impureté — l'appel modèle — n'entre JAMAIS ici : tout ce module est PUR et se
mesure sans clé ni réseau. La rédaction reste où elle est, pilotée PAR ce plan.
"""
import ingenierie_dc
import livrables


class AgentLivrable(object):
    """La configuration résolue d'un sujet de rédaction — réutilisable."""

    def __init__(self, type_id, phase=None, piece=None, rapide=False):
        self.type_id = str(type_id or "")
        self.phase = str(phase or "").strip().upper()[:12]
        self.piece = str(piece or "").strip().upper()[:16]
        self.rapide = bool(rapide)

    @property
    def id(self):
        base = self.type_id or "?"
        if self.phase and self.piece:
            base += ":%s/%s" % (self.phase, self.piece)
        return base + (":rapide" if self.rapide else "")

    def plan(self, inputs=None):
        """PURE. Le plan de récupération : requête, thèmes, sous-dossiers, mode.

        RIEN D'IMPUR ICI — aucun `rag`, aucun modèle. Le plan DIT quoi
        interroger et comment ; c'est la génération qui l'exécute.
        """
        inputs = inputs or {}
        _, themes = livrables.themes_du_type(self.type_id)
        pc = (ingenierie_dc.piece(self.phase, self.piece)
              if (self.phase and self.piece) else None)
        sous = (ingenierie_dc.sous_dossiers(pc["code"], pc.get("discipline"),
                                            phase=self.phase) if pc else [])
        return {
            "agent": self.id,
            "type": self.type_id,
            "requete": livrables.retrieval_query(self.type_id, inputs),
            # Le référentiel du sujet — « IEC 62443 », « NIS2 »… — quand la
            # console en désigne un ; sinon la liste est vide et le classement
            # se fait par pertinence seule, comme avant.
            "themes_groupe": list(themes),
            # L'aiguillage fin des pièces de centre de données (stade compris).
            "sous_dossiers": list(sous),
            # LE LEVIER DE RAPIDITÉ. `reclasser` False = on saute le juge.
            "reclasser": (not self.rapide),
            "compromis": ("" if not self.rapide else
                          "mode rapide : le re-classement par le juge est "
                          "sauté — réponse plus prompte, rappel un peu "
                          "moindre"),
        }


class Orchestrateur(object):
    """Route une demande vers son agent, RÉUTILISE le plan d'une demande à
    l'autre, et pilote la génération par ce plan. Il ne rédige pas."""

    def __init__(self):
        self._agents = {}

    def agent(self, type_id, phase=None, piece=None, rapide=False):
        cle = (str(type_id or ""),
               str(phase or "").strip().upper()[:12],
               str(piece or "").strip().upper()[:16],
               bool(rapide))
        a = self._agents.get(cle)
        if a is None:
            a = AgentLivrable(type_id, phase, piece, rapide)
            self._agents[cle] = a
        return a

    def plan(self, type_id, phase=None, piece=None, rapide=False, inputs=None):
        return self.agent(type_id, phase, piece, rapide).plan(inputs)

    def taille_cache(self):
        return len(self._agents)


# UN SEUL ORCHESTRATEUR POUR TOUT LE SERVICE — c'est ce qui rend le cache
# d'agents utile d'une demande à l'autre. Le créer par requête reviendrait à
# n'avoir aucun cache.
ORCHESTRATEUR = Orchestrateur()
