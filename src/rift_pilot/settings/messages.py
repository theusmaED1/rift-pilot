"""Mensagens em pt-BR usadas pelo TTS, interface gráfica e logs.

Único arquivo onde textos visíveis ao usuário podem ser definidos.
"""
from __future__ import annotations

import random


_POSITION_NAMES_PT_BR: dict[str, str] = {
    "TOP": "top",
    "JUNGLE": "selva",
    "MIDDLE": "mid",
    "BOTTOM": "bot",
    "UTILITY": "suporte",
    "NONE": "",
    "": "",
}


def translate_position(position: str) -> str:
    """Traduz o nome da posição da Live API para pt-BR usado nos anúncios."""
    return _POSITION_NAMES_PT_BR.get(position.upper(), "")


def _tts_skill(skill: str) -> str:
    """Converte o nome da skill para pronúncia clara no TTS pt-BR.

    'E' sozinho é lido como a conjunção; 'É' (acentuado) soa como a letra.
    """
    return "É" if skill == "E" else skill


class TTSMessages:
    """Mensagens faladas pelo coach via Edge TTS."""

    @staticmethod
    def skill_point_with_recommendation(skill: str) -> str:
        return f"Skill disponível! Upa o {_tts_skill(skill)} agora!"

    @staticmethod
    def skill_point_generic() -> str:
        return "Skill disponível! Upa agora!"

    @staticmethod
    def skill_points_accumulated(count: int) -> str:
        return f"{count} pontos de skill parados! Upa logo!"

    @staticmethod
    def gold_reached_for_item(item_name: str, following_name: str | None = None) -> str:
        base = f"Você já tem ouro para comprar {item_name}!"
        if following_name:
            base += f" Em seguida prepare {following_name}."
        return base

    @staticmethod
    def next_item_reminder(
        item_name: str,
        can_afford: bool,
        missing_boots: str | None,
        following_name: str | None = None,
    ) -> str:
        if can_afford:
            base = f"Próximo item: {item_name}. Você já pode comprar!"
        else:
            base = f"Próximo item: {item_name}."
        if following_name:
            base += f" Depois: {following_name}."
        if missing_boots:
            base += f" Botas: {missing_boots}."
        return base

    OBJECTIVE_DRAGON: dict[int, str] = {
        60: "1 minuto para o Dragão. Avise seu time!",
        30: "Dragão em 30 segundos. Avise o time!",
        10: "Dragão vai nascer em 10 segundos. Se prepara!",
    }

    OBJECTIVE_BARON: dict[int, str] = {
        60: "1 minuto para o Barão. Avise seu time!",
        30: "Barão em 30 segundos. Avise o time!",
        10: "Barão vai nascer em 10 segundos. Se prepara!",
    }

    OBJECTIVE_HERALD: dict[int, str] = {
        60: "1 minuto para o Arauto. Avise seu time!",
        30: "Arauto em 30 segundos. Avise o time!",
        10: "Arauto vai nascer em 10 segundos. Se prepara!",
    }

    TRINKET_REMINDERS: list[str] = [
        "Sua trinqueti está disponível! Lembre de usar!",
        "Trinqueti parada! Vai lá usar!",
        "Você não usa sua Trinqueti faz tempo!",
    ]

    MINIMAP_REMINDERS: list[str] = [
        "Olha o minimapa!",
        "Cheque o minimapa agora!",
        "Da uma olhada no minimapa!",
        "Minimapa! Confira!",
        "Veja o minimapa!",
        "Atenção ao minimapa!",
    ]

    OBJECTIVE_VOIDGRUBS: dict[int, str] = {
        60: "1 minuto para as Larvas. Avise seu time!",
        30: "Larvas em 30 segundos. Avise o time!",
        10: "Larvas vão nascer em 10 segundos. Se prepara!",
    }

    # Banco determinístico de farm: tone -> mode -> category -> [variantes].
    # category: farm_low, farm_good, farm_behind, farm_ahead, farm_highest.
    # Placeholders: {diff} e {enemy} apenas em farm_behind/farm_ahead.
    _FARM_MESSAGES: dict[str, dict[str, dict[str, list[str]]]] = {
        "neutral": {
            "simple": {
                "farm_low": [
                    "Farm abaixo do ritmo. Prioriza os minions.",
                    "Seu farm caiu. Volta para a wave.",
                    "Farm baixo agora. Foca nos last hits.",
                    "Recupera o farm. Não perde a próxima wave.",
                    "Ritmo de farm lento. Ajusta nos minions.",
                    "Você tá deixando farm passar. Reage.",
                    "Farm abaixo do ideal. Concentra na wave.",
                    "O farm precisa subir. Pega os próximos minions.",
                ],
                "farm_good": [
                    "Bom ritmo de farm. Mantém.",
                    "Farm constante. Continua assim.",
                    "Seu farm tá sólido. Não perde o foco.",
                    "Ritmo ideal de farm. Mantém o ritmo.",
                    "Você tá farmando bem. Continua.",
                    "Farm em dia. Segue nesse padrão.",
                    "Farm bem encaixado. Mantém.",
                    "Farm no ponto certo. Continua pressionando.",
                ],
                "farm_behind": [
                    "Você tá {diff} de farm atrás de {enemy}. Recupera.",
                    "{enemy} abriu {diff} de farm. Volta para a wave.",
                    "Você tá {diff} de farm abaixo de {enemy}. Reage.",
                    "{diff} atrás de {enemy} no farm. Foca nos minions.",
                    "Você perdeu espaço no farm para {enemy}. Recupera os {diff}.",
                    "{enemy} lidera por {diff} no farm. Ajusta o ritmo.",
                    "Farm {diff} abaixo de {enemy}. Prioriza last hits.",
                    "Diferença de {diff} de farm para {enemy}. Recupera agora.",
                ],
                "farm_ahead": [
                    "Você tá {diff} de farm à frente de {enemy}. Mantém.",
                    "{diff} de vantagem no farm sobre {enemy}. Continua.",
                    "Você lidera {enemy} por {diff} no farm. Mantém o ritmo.",
                    "Vantagem de {diff} de farm sobre {enemy}. Não relaxa.",
                    "Farm {diff} acima de {enemy}. Continua pressionando.",
                    "{enemy} tá {diff} atrás no farm. Mantém o controle.",
                    "Você abriu {diff} de farm sobre {enemy}. Continua firme.",
                    "{diff} de vantagem no farm sobre {enemy}. Mantém o ritmo.",
                ],
                "farm_highest": [
                    "Você tem o maior farm da partida. Continua.",
                    "Maior farm do jogo. Mantém o ritmo.",
                    "Ninguém tá farmando mais que você. Continua assim.",
                    "Você lidera o farm da partida. Não desacelera.",
                    "Top de farm da partida. Continua firme.",
                    "Maior farm entre todos. Mantém.",
                    "Você tá no topo do farm. Continua assim.",
                    "Liderança total de farm. Mantém o padrão.",
                ],
            },
            "explanatory": {
                "farm_low": [
                    "Farm baixo. Ouro de minion mantém seus itens no tempo certo.",
                    "Você tá atrasado no farm. Minion perdido atrasa sua força.",
                    "Farm abaixo do ideal. Cada wave perdida atrasa seu ouro.",
                    "Recupera o farm. Sem ouro constante, seu pico atrasa.",
                    "Farm fraco agora reduz sua pressão depois. Foca na wave.",
                    "Você tá perdendo ouro seguro. Prioriza os minions.",
                    "Farm atrasado é menos itens nas trocas. Reage.",
                    "Farm baixo tira sua força no meio do jogo. Volta para a wave.",
                ],
                "farm_good": [
                    "Bom farm. Esse ritmo garante itens no tempo certo.",
                    "Farm constante. Ouro estável mantém sua pressão.",
                    "Seu farm tá sólido. Continua somando vantagem.",
                    "Ritmo ideal. Esse ouro segura suas próximas lutas.",
                    "Você tá farmando bem. Isso mantém sua força ativa.",
                    "Farm em dia. Ouro de minion vale mais que jogada aleatória.",
                    "Boa execução no farm. Continua virando isso em vantagem.",
                    "Farm forte. Esse padrão te mantém relevante até o fim.",
                ],
                "farm_behind": [
                    "{diff} atrás de {enemy} no farm. Isso atrasa seus itens. Recupera.",
                    "{enemy} abriu {diff} de farm. Cada wave perdida aumenta a diferença.",
                    "Você tá {diff} abaixo de {enemy}. Foca nos minions antes de lutar.",
                    "{diff} abaixo de {enemy} no farm. Seus itens vão atrasar assim.",
                    "Você perdeu {diff} de farm para {enemy}. Reage antes da próxima luta.",
                    "{enemy} lidera por {diff} no farm. Prioriza last hits agora.",
                    "Farm {diff} abaixo de {enemy}. Menos ouro é menos pressão.",
                    "Diferença de {diff} para {enemy}. Ajusta a wave antes de girar.",
                ],
                "farm_ahead": [
                    "{diff} de vantagem no farm sobre {enemy}. Usa isso pra pressionar.",
                    "Você lidera {enemy} por {diff}. Item adiantado faz diferença.",
                    "Farm {diff} acima de {enemy}. Continua aumentando o controle.",
                    "{enemy} tá {diff} atrás no farm. Mantém a pressão da wave.",
                    "Você abriu {diff} de vantagem no farm. Usa pra ganhar espaço no mapa.",
                    "{diff} à frente de {enemy}. Seu ouro tá chegando antes.",
                    "Liderança de {diff} no farm. Continua forçando o ritmo.",
                    "Você tá {diff} acima de {enemy}. Mantém essa vantagem de ouro.",
                ],
                "farm_highest": [
                    "Maior farm da partida. Você tem vantagem de ouro sobre todos.",
                    "Top de farm do jogo. Continua usando essa pressão.",
                    "Você lidera o farm dos dez. Mantém o ritmo.",
                    "Maior farm da partida. Seus itens chegam antes nas lutas.",
                    "Ninguém farma mais que você. Continua virando isso em pressão.",
                    "Liderança total de farm. Esse ouro precisa virar controle.",
                    "Você é o maior farm da partida. Não deixa o ritmo cair.",
                    "Top de farm do jogo. Mantém o ritmo pra não perder a vantagem.",
                ],
            },
        },
        "funny": {
            "simple": {
                "farm_low": [
                    "Bora acordar! Farm tá fraquinho. Mete a foice nos minions!",
                    "Os minions tão morrendo de tédio te esperando. Farma!",
                    "Cadê o farm? Os minions sumiram da tua vida.",
                    "Tá namorando o minion? Mata logo e farma!",
                    "Farm tá em greve. Volta pra wave, campeão.",
                    "Esses minions não vão se matar sozinhos. Bora!",
                    "Farm anêmico detectado. Hora de comer minion.",
                    "Você e o farm terminaram? Reata essa relação.",
                ],
                "farm_good": [
                    "Isso aí! Farm tá voando, continua nessa pegada!",
                    "Minion não tem vez contigo. Continua!",
                    "Farm afiado! Os minions que se cuidem.",
                    "Tá comendo minion que é uma beleza. Segue!",
                    "Farm nota dez. Os minions te respeitam.",
                    "Você virou pesadelo de minion. Mantém!",
                    "Farm voando alto. Continua nessa!",
                    "Os minions já te conhecem pelo nome. Boa!",
                ],
                "farm_behind": [
                    "Ops! {diff} de farm atrás do {enemy} chato. Corre atrás!",
                    "{enemy} tá comendo teu farm também. {diff} na frente. Reage!",
                    "Tá deixando o {enemy} farmar sozinho? {diff} atrás. Bora!",
                    "{enemy} levou {diff} de farm teu. Vai buscar!",
                    "Eita, {diff} atrás do {enemy}. Acelera essa foice!",
                    "O {enemy} tá rindo com {diff} de farm a mais. Revida!",
                    "{diff} de farm atrás do {enemy}. Sai dessa, vai!",
                    "Deixou o {enemy} {diff} na frente. Corre pra wave!",
                ],
                "farm_ahead": [
                    "Mandou bem! {diff} na frente do {enemy}. Esmaga!",
                    "{enemy} comendo poeira: {diff} atrás de você. Continua!",
                    "Você tá {diff} na frente do {enemy}. Tá voando!",
                    "{diff} de farm a mais que o {enemy}. Show!",
                    "O {enemy} nem te alcança. {diff} na frente!",
                    "Tá dando aula pro {enemy}: {diff} de vantagem!",
                    "{diff} na frente do {enemy}. Ele que corra atrás!",
                    "Farm {diff} acima do {enemy}. Mantém o show!",
                ],
                "farm_highest": [
                    "Você é o rei do farm dessa partida! Continua!",
                    "Maior farmador do jogo! Os minions tremem!",
                    "Ninguém farma igual você. É lenda!",
                    "Top um de farm. Os minions fizeram um abaixo-assinado.",
                    "Você comeu mais minion que todo mundo. Respeito!",
                    "Maior farm da partida! Tá imparável!",
                    "Campeão do farm! Continua devorando!",
                    "Recorde de farm na sala. Não para!",
                ],
            },
            "explanatory": {
                "farm_low": [
                    "Farm fraco! Cada wave vale uns cem de ouro, tá deixando dinheiro na mesa.",
                    "Minion abandonado é item atrasado. Volta pra wave, vai!",
                    "Sem farm não tem itemzinho brilhante. Mata esses minions!",
                    "Farm baixo agora é você apanhando depois. Foca na wave!",
                    "Ouro de minion é o mais garantido do jogo. Não despreza!",
                    "Tá perdendo ouro fácil. Last hit paga teus itens, lembra?",
                    "Farm atrasado encurta tua força. Acelera essa foice!",
                    "Minion morto por outro é teu salário no bolso alheio. Farma!",
                ],
                "farm_good": [
                    "Farm voando! Esse ouro vira item na hora certa, continua!",
                    "Tá comendo minion certinho, é assim que se ganha item no tempo.",
                    "Farm afiado! Ouro constante segura tua força o jogo todo.",
                    "Boa! Esse ritmo te deixa forte até o fim, mantém!",
                    "Farm nota dez, item no tempo ganha troca, continua nessa!",
                    "Você no ritmo certo, farmar direito decide partida, segue!",
                    "Minion tremendo e tu enriquecendo. É esse o caminho!",
                    "Farm sólido vira vantagem real na luta. Mantém o show!",
                ],
                "farm_behind": [
                    "{diff} atrás do {enemy}, isso é quase um item de diferença, corre!",
                    "{enemy} {diff} na frente, cada wave perdida aumenta esse buraco. Reage!",
                    "Tá {diff} atrás do {enemy}, item atrasado perde troca. Vai pra wave!",
                    "{enemy} comeu {diff} a mais. Recupera antes que vire surra. Bora!",
                    "{diff} de farm pro {enemy}. Last hit fecha essa diferença, foca!",
                    "Deixou o {enemy} {diff} na frente, tua força atrasa assim. Acelera!",
                    "{enemy} lidera {diff}. Sem farm tu vira boneco na luta, reage!",
                    "{diff} pro {enemy}. Volta pro minion antes de girar o mapa!",
                ],
                "farm_ahead": [
                    "{diff} na frente do {enemy}, isso é item adiantado, usa pra pressionar!",
                    "Tá {diff} acima do {enemy}, item na frente ganha duelo, força troca!",
                    "{diff} de vantagem sobre o {enemy}. Vira esse ouro em objetivo!",
                    "Você farma {diff} a mais que o {enemy}. Pressiona enquanto dá!",
                    "{diff} liderando o {enemy}, vantagem real, não desperdiça!",
                    "Farm {diff} acima do {enemy}, tu bate mais forte, aproveita!",
                    "{diff} na frente do {enemy}. Item adiantado decide, força o ritmo!",
                    "Tá {diff} de farm acima, vira isso em controle de mapa, vai!",
                ],
                "farm_highest": [
                    "Maior farm da sala! Tu tem mais item que todo mundo, pressiona!",
                    "Top um de farm, esse ouro é vantagem na mão, usa!",
                    "Ninguém farma igual tu, vira em objetivo antes que sumam!",
                    "Maior farm da partida! Item adiantado ganha luta, força!",
                    "Tu lidera o farm dos dez. Isso é poder na mão, aproveita!",
                    "Recorde de farm! Tua vantagem some se parar, não para!",
                    "Maior farmador do jogo, bate mais forte que a média, usa isso!",
                    "Top de ouro por farm. Vira isso em pressão de mapa, lenda!",
                ],
            },
        },
        "serious": {
            "simple": {
                "farm_low": [
                    "Farm crítico. Todo recurso para os minions agora.",
                    "Farm atrasado. Corrige imediatamente.",
                    "Farm abaixo do mínimo. Prioriza a wave.",
                    "Farm insuficiente. Foco total em last hits.",
                    "Farm muito baixo. Ajusta agora.",
                    "Farm fora do esperado. Concentra na wave.",
                    "Ritmo de farm ruim. Corrige.",
                    "Farm abaixo do padrão. Recupera já.",
                ],
                "farm_good": [
                    "Farm dentro do ideal. Mantém o ritmo.",
                    "Farm adequado. Mantém.",
                    "Farm no alvo. Mantém a execução.",
                    "Ritmo de farm correto. Não desvia.",
                    "Farm conforme o esperado. Continua.",
                    "Farm sólido. Mantém.",
                    "Farm dentro do esperado. Mantém.",
                    "Padrão de farm atingido. Mantém.",
                ],
                "farm_behind": [
                    "Você está {diff} de farm atrás de {enemy}. Prioridade absoluta.",
                    "{enemy} lidera por {diff}. Corrige o farm imediatamente.",
                    "Diferença de {diff} para {enemy}. Foco total na wave.",
                    "{diff} abaixo de {enemy}. Recupera agora.",
                    "Desvantagem de {diff} de farm contra {enemy}. Reage.",
                    "{enemy} à frente por {diff}. Prioriza last hits.",
                    "Atraso crítico: {diff} atrás de {enemy}. Corrige.",
                    "Farm {diff} abaixo de {enemy}. Ação imediata.",
                ],
                "farm_ahead": [
                    "Vantagem de {diff} de farm sobre {enemy}. Vira em pressão.",
                    "{diff} à frente de {enemy}. Mantém e explora.",
                    "Liderança de {diff} sobre {enemy}. Mantém.",
                    "{diff} acima de {enemy}. Vira em objetivo.",
                    "Vantagem de {diff} contra {enemy}. Não desperdiça.",
                    "{enemy} atrás por {diff}. Pressiona.",
                    "Farm {diff} sobre {enemy}. Usa a vantagem.",
                    "Liderança de {diff} no farm. Mantém.",
                ],
                "farm_highest": [
                    "Maior farm da partida. Mantém a execução.",
                    "Liderança de farm absoluta. Mantém.",
                    "Top de farm do jogo. Não desvia.",
                    "Maior farm entre os dez. Mantém.",
                    "Liderança de ouro por farm. Mantém.",
                    "Farm máximo da partida. Mantém.",
                    "Farm líder da partida. Continua.",
                    "Topo do farm. Mantém o ritmo.",
                ],
            },
            "explanatory": {
                "farm_low": [
                    "Farm crítico. Ouro de minion é a fonte mais estável; perder isso reduz sua força.",
                    "Farm atrasado adia itens importantes e enfraquece suas trocas. Corrige.",
                    "Farm abaixo do mínimo. Cada wave perdida é força de luta adiada.",
                    "Farm insuficiente atrasa seus itens. Prioriza a wave imediatamente.",
                    "Farm muito baixo. Item atrasado perde confronto direto.",
                    "Farm fora do esperado. Ouro constante define sua força no fim do jogo.",
                    "Ritmo de farm ruim. Sem itens no tempo, sua força cai.",
                    "Farm abaixo do padrão. Recupera: a diferença de ouro cresce a cada wave.",
                ],
                "farm_good": [
                    "Farm no ideal. Item no tempo certo sustenta vantagem nas trocas.",
                    "Farm adequado. Ouro constante mantém sua força em todas as fases.",
                    "Farm no alvo. Esse ritmo garante sua força no tempo certo.",
                    "Execução correta. Farmar bem é o fator mais decisivo no longo prazo.",
                    "Farm conforme esperado. Item no tempo decide as lutas.",
                    "Padrão atingido. Ouro estável vira controle de mapa.",
                    "Execução sólida. Mantém: farm constante supera kill isolada.",
                    "Farm no esperado. Esse ouro define sua eficácia nas lutas.",
                ],
                "farm_behind": [
                    "Você está {diff} atrás de {enemy}: cerca de um item de diferença em força.",
                    "{enemy} lidera por {diff}. A diferença cresce a cada wave não recuperada.",
                    "Diferença de {diff} para {enemy}. Item atrasado perde confronto direto.",
                    "{diff} abaixo de {enemy}. Recupera antes que vire desvantagem irreversível.",
                    "Desvantagem de {diff} contra {enemy}. Prioriza last hits sobre rotação.",
                    "{enemy} à frente por {diff}. Sem recuperar, sua força cai.",
                    "Atraso de {diff} para {enemy}. Cada minion perdido prolonga a desvantagem.",
                    "Farm {diff} abaixo de {enemy}. Ação imediata na wave reduz a diferença.",
                ],
                "farm_ahead": [
                    "Vantagem de {diff} sobre {enemy}: cerca de um item de força a mais. Explora.",
                    "{diff} à frente de {enemy}. Item adiantado vence duelo; força as trocas.",
                    "Liderança de {diff} sobre {enemy}. Vira em controle de objetivo.",
                    "{diff} acima de {enemy}. A vantagem de itens é temporária; pressiona agora.",
                    "Vantagem de {diff} contra {enemy}. Usa a força antes que ele alcance.",
                    "{enemy} atrás por {diff}. Item adiantado decide confronto; explora.",
                    "Farm {diff} sobre {enemy}. Vira ouro em pressão de mapa.",
                    "Liderança de {diff}. Mantém o ritmo: a vantagem se sustenta com constância.",
                ],
                "farm_highest": [
                    "Maior farm da partida. Vantagem de itens sobre todos; vira em objetivo.",
                    "Liderança absoluta de farm. Esse ouro é força de luta acima da média.",
                    "Top de farm do jogo. Item adiantado decide as lutas; explora.",
                    "Maior farm entre os dez. A vantagem some se o ritmo cair; mantém.",
                    "Liderança de ouro por farm. Vira em controle de mapa imediato.",
                    "Farm máximo da partida. Sua força está acima da média; usa.",
                    "Farm líder da partida. Vantagem concreta em toda luta; mantém.",
                    "Topo do farm. A liderança exige constância para se manter.",
                ],
            },
        },
        "tryhard": {
            "simple": {
                "farm_low": [
                    "Farm inaceitável. Para de errar last hit e foca.",
                    "Esse farm não ganha jogo. Sobe agora.",
                    "Farm de bronze. Acorda e pega a wave.",
                    "Você tá jogando fora o farm. Corrige já.",
                    "Farm ruim demais pra esse tempo. Sem desculpa, farma.",
                    "Inadmissível esse farm. Mete pressão na wave.",
                    "Farm fraco demais. Quem quer ganhar farma.",
                    "Para de vacilar no farm. Foco total agora.",
                ],
                "farm_good": [
                    "Farm decente. Agora não cai o ritmo.",
                    "Tá no padrão. Não relaxa, sobe mais.",
                    "Farm ok. Quem quer subir não para aqui.",
                    "Bom farm. Mantém e cobra mais de você.",
                    "Farm correto. Agora não erra mais nenhum.",
                    "No alvo. Não comemora, executa.",
                    "Farm sólido. Próximo nível: zero erro.",
                    "Tá indo. Mantém o foco no farm.",
                ],
                "farm_behind": [
                    "{diff} atrás do {enemy}. Inaceitável. Reage agora.",
                    "{enemy} te lavando por {diff}. Acorda e farma.",
                    "Perdendo {diff} pro {enemy}? Sem desculpa. Sobe.",
                    "{diff} atrás do {enemy}. Quem quer ganhar não aceita isso.",
                    "Tá {diff} abaixo do {enemy}. Foca e zera essa diferença.",
                    "{enemy} {diff} na frente. Para de vacilar e recupera.",
                    "{diff} atrás do {enemy}. Reage agora ou perde.",
                    "{diff} atrás do {enemy}. Vira esse jogo no farm.",
                ],
                "farm_ahead": [
                    "{diff} na frente do {enemy}. Agora abre mais essa diferença.",
                    "Lavando o {enemy} por {diff}. Não para, esmaga.",
                    "{diff} acima do {enemy}. Pressão total agora.",
                    "{enemy} {diff} atrás. Sufoca, não dá espaço.",
                    "{diff} de vantagem no {enemy}. Vira isso em abate.",
                    "Tá dominando o {enemy}: {diff}. Mantém o pé no acelerador.",
                    "{diff} na frente do {enemy}. Fecha o jogo.",
                    "Vantagem de {diff} no {enemy}. Não alivia, esmaga.",
                ],
                "farm_highest": [
                    "Maior farm da partida. Agora carrega esse jogo.",
                    "Top um de farm. Não relaxa, fecha a partida.",
                    "Ninguém farma como você. Vira isso em vitória.",
                    "Maior farm do jogo. Agora domina o mapa.",
                    "Líder de farm. Carrega ou não adianta nada.",
                    "Top de farm. Pressão máxima agora.",
                    "Farm número um. Vira isso em objetivo já.",
                    "Maior farm da sala. Fecha o jogo, sem vacilo.",
                ],
            },
            "explanatory": {
                "farm_low": [
                    "Farm inaceitável. Cada last hit perdido é item atrasado e troca perdida. Foca.",
                    "Esse farm não ganha jogo: sem itens no tempo você vira figurante. Sobe agora.",
                    "Farm fraco atrasa tua força. Quem quer subir de elo não aceita isso. Corrige.",
                    "Você tá doando ouro de graça. Last hit constante é o que paga sua build. Acorda.",
                    "Farm ruim pra esse tempo. A diferença só cresce; recupera antes que vire surra.",
                    "Inadmissível. Ouro de minion é o mais estável do jogo, não despreza. Foca.",
                    "Farm baixo é derrota adiada. Sem itens você perde toda troca. Sobe.",
                    "Para de vacilar: cada wave perdida encurta tua força. Farma já.",
                ],
                "farm_good": [
                    "Farm no padrão. Item no tempo certo separa quem sobe de quem fica. Mantém.",
                    "Tá correto. Farmar bem decide partida mais que qualquer abate. Não cai.",
                    "Bom ritmo. Esse ouro garante tua força, mantém e não erra mais nenhum.",
                    "Farm sólido. Quem quer carregar mantém isso a partida toda. Segue.",
                    "No alvo. Item no tempo ganha luta; é assim que se fecha jogo. Mantém.",
                    "Farm certo. Agora vira essa constância em vantagem real. Não relaxa.",
                    "Padrão atingido. O próximo nível é manter isso sob pressão. Executa.",
                    "Bom farm. Ouro estável vira controle de mapa, não desperdiça. Sobe.",
                ],
                "farm_behind": [
                    "{diff} atrás do {enemy}: quase um item a menos. Inaceitável pra quem quer ganhar. Reage.",
                    "{enemy} {diff} na frente e a diferença cresce a cada wave. Sem farm tu vira boneco. Sobe.",
                    "Perdendo {diff} pro {enemy}, item atrasado perde toda troca. Recupera agora.",
                    "{diff} abaixo do {enemy}. Cada minion dele a mais é tua força adiada. Foca.",
                    "{diff} atrás do {enemy}. Sem reagir, esse jogo já era. Vai pra wave.",
                    "{enemy} te lava por {diff}. Quem sobe de elo zera isso rápido. Executa.",
                    "{diff} atrás do {enemy}: desvantagem real. Recupera antes de girar.",
                    "{diff} pro {enemy}. Last hit constante é a única saída. Sem desculpa.",
                ],
                "farm_ahead": [
                    "{diff} na frente do {enemy}: item adiantado. Usa essa força pra fechar, não alivia.",
                    "Lavando o {enemy} por {diff}. Item na frente ganha duelo, pressiona agora.",
                    "{diff} acima do {enemy}. Essa diferença é poder; vira em abate ou objetivo já.",
                    "{enemy} {diff} atrás. Quem quer ganhar sufoca aqui, não dá respiro. Esmaga.",
                    "{diff} de vantagem no {enemy}: item na frente decide. Força troca agora.",
                    "Dominando o {enemy} por {diff}. Vantagem some se parar, mantém o acelerador.",
                    "{diff} na frente do {enemy}. Vira ouro em pressão de mapa. Fecha.",
                    "Vantagem de {diff} no {enemy}. Tua força tá no pico; usa antes que ele alcance.",
                ],
                "farm_highest": [
                    "Maior farm da partida: mais itens que todos. Agora carrega ou não vale nada.",
                    "Top um de farm. Esse ouro é vantagem real, vira em vitória, não relaxa.",
                    "Ninguém farma como você. Item adiantado decide luta; fecha o jogo agora.",
                    "Maior farm do jogo. Vantagem some se o ritmo cair, domina o mapa já.",
                    "Líder de farm dos dez. Tu bate mais forte que todos; pressão total agora.",
                    "Top de ouro por farm. Quem carrega usa isso pra fechar, sem vacilo.",
                    "Farm número um. Vira vantagem de item em objetivo antes que sumam.",
                    "Maior farm da sala. Esse é o momento de virar isso em vitória. Executa.",
                ],
            },
        },
        "sarcastic": {
            "simple": {
                "farm_low": [
                    "Que farm impressionante. De ruim. Volta pra wave.",
                    "Os minions agradecem a piedade. Que tal matar eles?",
                    "Belo farm. Se o objetivo for perder. Foca.",
                    "Nossa, que ritmo de farm. Quase um espectador.",
                    "Continua assim que o inimigo agradece. Farma.",
                    "Farm digno de tutorial. E olha que nem isso.",
                    "Tá esperando o minion morrer de velhice? Farma.",
                    "Que ideia ousada ignorar o farm. Para.",
                ],
                "farm_good": [
                    "Olha só, sabe farmar. Quem diria. Mantém.",
                    "Surpreendente: o farm tá decente. Continua.",
                    "Até que enfim um farm aceitável. Não estraga.",
                    "Milagre, o farm tá em dia. Mantém.",
                    "Veja só, last hit funcionando. Continua.",
                    "Inacreditável, farm no ritmo. Não relaxa.",
                    "Que novidade, farmando direito. Mantém.",
                    "O farm decidiu aparecer hoje. Aproveita.",
                ],
                "farm_behind": [
                    "{diff} atrás do {enemy}. Mas claro, farm é só detalhe.",
                    "O {enemy} agradece os {diff} de vantagem. Reage.",
                    "Só {diff} atrás do {enemy}. Nada de mais, né? Farma.",
                    "{enemy} {diff} na frente. Mas tá tudo sob controle, claro.",
                    "Que generoso doar {diff} de farm pro {enemy}. Para.",
                    "{diff} atrás do {enemy}. Plano brilhante. Recupera.",
                    "O {enemy} te agradece pelos {diff}. Volta pra wave.",
                    "Só {diff} atrás do {enemy}. Tranquilo, né? Foca.",
                ],
                "farm_ahead": [
                    "{diff} na frente do {enemy}. Olha, um acerto. Mantém.",
                    "Surpresa: {diff} acima do {enemy}. Não estraga.",
                    "{diff} à frente do {enemy}. Quem diria. Continua.",
                    "Veja só, {diff} na frente do {enemy}. Mantém isso.",
                    "Milagre: {diff} acima do {enemy}. Não relaxa agora.",
                    "{diff} de vantagem no {enemy}. Aproveita enquanto dura.",
                    "Olha você liderando o {enemy} por {diff}. Mantém.",
                    "{diff} na frente do {enemy}. Até que enfim. Mantém.",
                ],
                "farm_highest": [
                    "Maior farm da partida. Sentou e funcionou. Continua.",
                    "Olha só, top de farm. Quem diria. Mantém.",
                    "Surpreendente: maior farm do jogo. Não estraga.",
                    "Você liderando o farm. Milagre acontece. Segue.",
                    "Maior farm da sala. Aproveita a fama. Continua.",
                    "Que novidade, top um de farm. Mantém.",
                    "Veja só, o maior farm. Não relaxa agora.",
                    "Top de farm da partida. Impressionante. Mantém.",
                ],
            },
            "explanatory": {
                "farm_low": [
                    "Belo farm. Pena que cada wave ignorada é cem de ouro no lixo. Foca.",
                    "Que ousadia ignorar o farm. Item atrasado perde troca, mas detalhe. Volta.",
                    "Os minions agradecem o descanso. Você é que perde força. Farma.",
                    "Farm de espectador. Ouro de minion é o mais estável do jogo, sabia? Para.",
                    "Continua assim: o inimigo adora teu item atrasado. Last hit, lembra dele?",
                    "Que plano genial pular o farm. Sem item no tempo você vira figurante. Foca.",
                    "Impressionante doar ouro de wave. Tua força agradece a demora. Para.",
                    "Farm digno de tutorial. E olha que nem o tutorial erra tanto. Volta.",
                ],
                "farm_good": [
                    "Olha, farmando direito. Item no tempo certo até ganha troca. Mantém, surpresa.",
                    "Milagre: farm constante. Sabia que isso decide partida mais que abate? Continua.",
                    "Até que enfim ouro estável. Quem diria que farmar segura sua força. Não estraga.",
                    "Inacreditável, last hit funcionando. Isso é vantagem real na luta. Mantém.",
                    "Veja só, farm no ritmo. Esse ouro vira item no tempo e decide luta. Segue.",
                    "Que novidade, farm decente. Farmar bem supera abate isolado, repara. Continua.",
                    "O farm resolveu aparecer. Aproveita: item no tempo ganha confronto. Mantém.",
                    "Surpresa boa, farm em dia. É o que mais decide no longo prazo. Não cai.",
                ],
                "farm_behind": [
                    "{diff} atrás do {enemy}. Quase um item a menos, mas farm é só detalhe, claro.",
                    "O {enemy} agradece {diff} de vantagem, diferença que só cresce a cada wave. Reage.",
                    "Só {diff} atrás do {enemy}. Item atrasado perde troca, mas tá tudo bem, né?",
                    "{enemy} {diff} na frente. Tua força atrasou, mas quem liga. Recupera.",
                    "Generoso doar {diff} pro {enemy}: ele fica mais forte com isso. Volta pra wave.",
                    "{diff} atrás do {enemy}. Plano brilhante adiar teus itens. Foca antes que piore.",
                    "O {enemy} te agradece {diff}, desvantagem real, mas detalhe. Reage.",
                    "Só {diff} atrás do {enemy}. Cada minion dele a mais te enterra. Tranquilo?",
                ],
                "farm_ahead": [
                    "{diff} na frente do {enemy}. Um acerto: item adiantado ganha duelo. Usa, vai.",
                    "Surpresa, {diff} acima do {enemy}. Essa vantagem some se você relaxar. Pressiona.",
                    "{diff} à frente do {enemy}. Quem diria, vira essa força em objetivo. Continua.",
                    "Veja só, {diff} na frente do {enemy}. Item adiantado decide; força troca, vai.",
                    "Milagre: {diff} acima do {enemy}. Vantagem temporária, usa antes que alcance.",
                    "{diff} de vantagem no {enemy}. Aproveita: ouro na frente vira pressão de mapa.",
                    "Olha você {diff} liderando o {enemy}. Não desperdiça essa força. Força.",
                    "{diff} na frente do {enemy}. Até que enfim útil, vira em abate, não dorme.",
                ],
                "farm_highest": [
                    "Maior farm da partida. Sentou e funcionou, agora vira em objetivo, vai.",
                    "Top de farm, quem diria. Esse ouro é vantagem real; usa antes que suma.",
                    "Surpreendente liderar o farm. Item adiantado decide luta, pressiona.",
                    "Maior farm do jogo. Milagre. Vantagem some se o ritmo cair, não relaxa.",
                    "Você no topo do farm. Aproveita: tu bate mais forte que a média agora. Força.",
                    "Que novidade, top um de farm. Vira em controle de mapa antes que sumam.",
                    "Veja só, o maior farm. Vantagem concreta na luta, usa, não fica admirando.",
                    "Top de farm da partida. Impressionante. Agora vira isso em vitória, vai.",
                ],
            },
        },
    }

    _FARM_FALLBACK = "Farm abaixo do esperado."

    @staticmethod
    def _farm_pick(
        category: str,
        tone: str,
        mode: str,
        recent: tuple[str, ...] = (),
        **fmt: object,
    ) -> tuple[str, str]:
        """Escolhe uma variante fora da janela `recent`.

        Retorna (template_cru, frase_formatada). O template cru é o que o
        chamador empilha na janela anti-repetição; a formatada é o que o TTS
        fala. A escolha opera no template (antes do .format) porque {diff}/
        {enemy} variam entre chamadas e quebrariam a comparação de janela.
        """
        by_mode = TTSMessages._FARM_MESSAGES.get(
            tone, TTSMessages._FARM_MESSAGES["neutral"]
        )
        by_cat = by_mode.get(mode, by_mode["simple"])
        variants = by_cat.get(category) or [TTSMessages._FARM_FALLBACK]
        pool = [v for v in variants if v not in recent] or variants
        template = random.choice(pool)
        return template, template.format(**fmt)

    @staticmethod
    def farm_low(
        tone: str = "neutral", mode: str = "simple", recent: tuple[str, ...] = ()
    ) -> tuple[str, str]:
        """Alerta de farm geral abaixo do ideal. Retorna (template, frase)."""
        return TTSMessages._farm_pick("farm_low", tone, mode, recent)

    @staticmethod
    def boots_reminder(boots_name: str) -> str:
        return f"Não esqueça das botas: {boots_name}."

    @staticmethod
    def farm_good(
        tone: str = "neutral", mode: str = "simple", recent: tuple[str, ...] = ()
    ) -> tuple[str, str]:
        """Elogio de farm no ritmo ideal. Retorna (template, frase)."""
        return TTSMessages._farm_pick("farm_good", tone, mode, recent)

    @staticmethod
    def farm_behind(
        diff_cs: int,
        enemy_name: str = "inimigo",
        tone: str = "neutral",
        mode: str = "simple",
        recent: tuple[str, ...] = (),
    ) -> tuple[str, str]:
        """Alerta de farm atrás do inimigo de lane. Retorna (template, frase)."""
        return TTSMessages._farm_pick(
            "farm_behind", tone, mode, recent, diff=diff_cs, enemy=enemy_name
        )

    @staticmethod
    def farm_ahead(
        diff_cs: int,
        enemy_name: str = "inimigo",
        tone: str = "neutral",
        mode: str = "simple",
        recent: tuple[str, ...] = (),
    ) -> tuple[str, str]:
        """Incentivo de farm à frente do inimigo de lane. Retorna (template, frase)."""
        return TTSMessages._farm_pick(
            "farm_ahead", tone, mode, recent, diff=diff_cs, enemy=enemy_name
        )

    @staticmethod
    def farm_highest(
        tone: str = "neutral", mode: str = "simple", recent: tuple[str, ...] = ()
    ) -> tuple[str, str]:
        """Parabéns por ter o maior farm da partida. Retorna (template, frase)."""
        return TTSMessages._farm_pick("farm_highest", tone, mode, recent)

    @staticmethod
    def build_introduction(champion: str, role: str) -> str:
        if role:
            return f"{champion} no {role}."
        return f"Jogando de {champion}."

    @staticmethod
    def build_starters(starter_items: list[str]) -> str:
        return "Comece com " + " e ".join(starter_items) + "."

    @staticmethod
    def build_core(core_items: list[str]) -> str:
        return "Core: " + ", ".join(core_items) + "."

    @staticmethod
    def build_boots(boots: str) -> str:
        return f"Botas: {boots}."

    @staticmethod
    def build_max_order(skill_priority: list[str]) -> str:
        order = " depois o ".join(_tts_skill(s) for s in skill_priority)
        return f"Maximize {order}."

    @staticmethod
    def build_quest_item(item_name: str) -> str:
        return f"Na quest, escolha: {item_name}."

    @staticmethod
    def quest_item_available(item_name: str) -> str:
        return f"Quest completa! Escolha agora: {item_name}!"


class UILabels:
    """Textos exibidos na interface gráfica."""

    APP_TITLE = "Rift Pilot"
    APP_SUBTITLE = "Seu coach de voz para League of Legends"

    STATUS_HEADER = "STATUS"
    STATUS_WAITING = "Aguardando o jogo iniciar..."
    STATUS_CONNECTING = "Conectando..."
    STATUS_WAITING_GAME = "Aguardando o jogo..."
    STATUS_LOADING_SCREEN = "Tela de carregamento — buscando build..."
    STATUS_MONITORING = "Monitorando"
    STATUS_GAME_OVER = "Jogo encerrado."

    SECTION_BUILD = "BUILD RECOMENDADA"
    SECTION_FEATURES = "AVISOS ATIVOS"
    SECTION_LOG = "LOG DE EVENTOS"

    BUTTON_START = "▶  INICIAR"
    BUTTON_STOP = "■  PARAR"
    BUTTON_CLEAR_LOG = "LIMPAR"

    BUILD_PLACEHOLDER = "—"
    BUILD_ROW_STARTERS = ("Início", "◆")
    BUILD_ROW_CORE = ("Core", "⚔")
    BUILD_ROW_BOOTS = ("Botas", "⚡")
    BUILD_ROW_SKILLS = ("Skills", "≡")
    BUILD_ROW_RUNES = ("Runas", "✦")
    BUILD_ROW_QUEST = ("Quest", "⚙")

    FEATURE_SKILL_TITLE = "Pontos de skill disponíveis"
    FEATURE_SKILL_DESCRIPTION = "Avisa quando você sobe de nível e tem skill para evoluir"
    FEATURE_SKILL_ICON = "✦"

    FEATURE_OBJECTIVES_TITLE = "Objetivos (Dragão, Barão, Arauto, Larvas)"
    FEATURE_OBJECTIVES_DESCRIPTION = "Anuncia o spawn e o status dos objetivos do mapa"
    FEATURE_OBJECTIVES_ICON = "♛"

    FEATURE_BUILD_ANNOUNCE_TITLE = "Anunciar build no início da partida"
    FEATURE_BUILD_ANNOUNCE_DESCRIPTION = "Lê em voz alta a build recomendada quando o jogo começa"
    FEATURE_BUILD_ANNOUNCE_ICON = "►"

    FEATURE_NEXT_ITEM_TITLE = "Lembrete do próximo item da build"
    FEATURE_NEXT_ITEM_DESCRIPTION = "Toca um aviso quando você tem ouro para o próximo item"
    FEATURE_NEXT_ITEM_ICON = "●"

    FEATURE_MINIMAP_TITLE = "Lembrete do minimapa"
    FEATURE_MINIMAP_DESCRIPTION = "Avisa periodicamente para checar o minimapa"
    FEATURE_MINIMAP_ICON = "◎"

    FEATURE_TRINKET_TITLE = "Lembrete de trinket"
    FEATURE_TRINKET_DESCRIPTION = "Avisa quando sua trinket está disponível há mais de 1 minuto"
    FEATURE_TRINKET_ICON = "◈"

    FEATURE_FARM_TITLE = "Feedback de farm"
    FEATURE_FARM_DESCRIPTION = "Avisa quando seu farm está abaixo do esperado ou atrás do inimigo"
    FEATURE_FARM_ICON = "◉"

    FEATURE_AI_BUILD_TITLE = "Build por IA (requer chave Groq)"
    FEATURE_AI_BUILD_DESCRIPTION = "Usa modelo gpt-oss-120b para decisões de build inteligentes"
    FEATURE_AI_BUILD_ICON = "🤖"

    SECTION_COACH_CONFIG = "CONFIGURAÇÕES DO COACH"
    CONFIG_TONE_LABEL = "Tom"
    CONFIG_MODE_LABEL = "Detalhe"
    CONFIG_TONE_NEUTRAL = "Neutro"
    CONFIG_TONE_FUNNY = "Engraçado"
    CONFIG_TONE_SERIOUS = "Sério"
    CONFIG_TONE_TRYHARD = "Tryhard"
    CONFIG_TONE_SARCASTIC = "Sarcástico"
    CONFIG_MODE_SIMPLE = "Simples"
    CONFIG_MODE_EXPLANATORY = "Explicativo"

    FOOTER_TTS_INFO = "◄)) EDGE TTS — PT-BR-ANTONIONEURAL"

    CLI_DESCRIPTION = "Rift Pilot — modo CLI (replay e testes)"
    CLI_REPLAY_HELP = "Arquivo .jsonl gerado por scripts/log_game.py"
    CLI_VOICE_HELP = "Voz Edge TTS (padrão: pt-BR-AntonioNeural)"


class LogMessages:
    """Mensagens estruturadas exibidas no painel de log e na CLI."""

    APP_INITIALIZED = "Aplicação inicializada com sucesso."
    TTS_LOADED = "Módulo TTS: AntonioNeural (pt-BR) carregado."
    WAITING_USER_START = "Aguardando comando para iniciar a sessão."
    GAME_CONNECTED = "● Conectado ao jogo!"
    LOADING_SCREEN_DETECTED = "◌ Tela de carregamento detectada — buscando build..."
    GAME_ENDED = "— Jogo encerrado."
    CLI_MONITORING = "Monitorando... (Ctrl+C para parar)"
    CLI_STOPPED_BY_USER = "Encerrado."

    @staticmethod
    def build_loaded(champion: str, source: str) -> str:
        return f"✓ Build de {champion} carregada (fonte: {source})"

    @staticmethod
    def build_not_found(champion: str) -> str:
        return f"× Build não encontrada para {champion}"

    @staticmethod
    def build_fetch_error(error: str) -> str:
        return f"× Erro ao buscar build: {error}"

    @staticmethod
    def coach_event(game_time_seconds: float, message: str) -> str:
        return f"[{game_time_seconds:.0f}s] {message}"
