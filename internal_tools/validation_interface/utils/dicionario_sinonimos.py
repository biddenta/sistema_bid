SINONIMOS_PRODUTOS_DENTAIS = {
    # === MATERIAIS RESTAURADORES ===
    "resina": ["composite", "compósito", "fotopolimerizável", "foto", "resto"],
    "composite": ["resina", "compósito", "fotopolimerizável"],
    "compósito": ["resina", "composite", "fotopolimerizável"],
    "fotopolimerizável": ["resina", "composite", "foto"],
    
    # === ANESTÉSICOS ===
    "anestésico": ["anestesia", "lidocaína", "articaína", "mepivacaína"],
    "lidocaína": ["anestésico", "anestesia", "xylocaína"],
    "articaína": ["anestésico", "anestesia", "ultracaína"],
    "mepivacaína": ["anestésico", "anestesia", "scandicaína"],
    
    # === INSTRUMENTAIS ===
    "broca": ["fresa", "ponta", "diamantada", "carbide"],
    "fresa": ["broca", "ponta", "diamantada"],
    "ponta": ["broca", "fresa", "diamantada"],
    "cureta": ["raspador", "instrumento periodontal"],
    "sonda": ["explorador", "instrumento diagnóstico"],
    
    # === MATERIAIS ENDODÔNTICOS ===
    "lima": ["instrumento endodôntico", "k-file", "h-file"],
    "guta": ["guta-percha", "obturação", "cone"],
    "cimento": ["selador", "sealer", "vedamento"],
    "irrigação": ["hipoclorito", "edta", "solução"],
    
    # === ORTODONTIA ===
    "bracket": ["bráquete", "suporte ortodôntico"],
    "bráquete": ["bracket", "suporte ortodôntico"],
    "fio": ["arco", "wire", "ortodôntico"],
    "elástico": ["elastic", "ligadura"],
    
    # === PRÓTESE ===
    "moldagem": ["impressão", "molde", "alginato"],
    "impressão": ["moldagem", "molde"],
    "silicone": ["polivinilsiloxano", "pvs", "condensação"],
    "gesso": ["modelo", "fundição"],
    
    # === CIRURGIA ===
    "bisturi": ["lâmina", "cabo", "surgical"],
    "sutura": ["fio de sutura", "agulha", "síntese"],
    "extração": ["exodontia", "remoção", "cirurgia"],
    
    # === PREVENÇÃO ===
    "flúor": ["fluoreto", "verniz", "aplicação tópica"],
    "selante": ["pit and fissure", "proteção oclusal"],
    "profilaxia": ["limpeza", "tartarectomia", "raspagem"],
    
    # === MARCAS COMUNS ===
    "3m": ["scotchbond", "filtek", "espe"],
    "dentsply": ["maillefer", "sirona", "tulsa"],
    "ultradent": ["opalescence", "matrix"],
    "angelus": ["sealer 26", "pro root"],
    "fgm": ["whiteness", "opallis"],
    "ivoclar": ["tetric", "vivadent"],
    "kerr": ["optibond", "sonicfill"],
    "kulzer": ["charisma", "venus"],
    
    # === TIPOS DE PRODUTO ===
    "kit": ["conjunto", "estojo", "sistema"],
    "conjunto": ["kit", "estojo", "sistema"],
    "refil": ["recarga", "reposição", "refill"],
    "seringa": ["carpule", "tubo", "aplicador"],
    
    # === MEDIDAS E QUANTIDADES ===
    "ml": ["mililitro", "cc"],
    "mg": ["miligrama", "miligramas"],
    "gr": ["gramas", "g"],
    "un": ["unidade", "unidades", "pç", "peça"],
    "cx": ["caixa", "box"],
    
    # === CORES E TONS ===
    "a1": ["natural", "claro"],
    "a2": ["marfim", "ivory"],
    "a3": ["natural médio"],
    "b1": ["amarelado claro"],
    "universal": ["qualquer cor", "todas as cores"],
    
    # === ESPECIALIDADES ===
    "endodontia": ["endo", "canal", "tratamento de canal"],
    "periodontia": ["perio", "gengiva", "periodontal"],
    "ortodontia": ["orto", "aparelho", "alinhamento"],
    "implantodontia": ["implante", "osseointegração"],
    "prótese": ["protética", "reabilitação oral"],
    "cirurgia": ["buco-maxilo", "oral", "exodontia"],
    
    # === CARACTERÍSTICAS TÉCNICAS ===
    "radiopaco": ["radiodenso", "visível raio-x"],
    "biocompatível": ["atóxico", "seguro"],
    "hidrofílico": ["afinidade água"],
    "hidrofóbico": ["repele água"],
    "antimicrobiano": ["antibacteriano", "antisséptico"],
}

# Abreviações comuns
ABREVIACOES = {
    "endo": "endodontia",
    "perio": "periodontia", 
    "orto": "ortodontia",
    "protese": "prótese",
    "cir": "cirurgia",
    "rest": "restauração",
    "prev": "prevenção",
    "anesth": "anestésico",
    "comp": "composite",
    "res": "resina",
    "fluor": "flúor",
    "cert": "certificado",
    "reg": "registro",
    "anvisa": "agência nacional vigilância sanitária",
    "iso": "international organization standardization",
    "fda": "food drug administration",
    "prof": "profissional",
    "odonto": "odontologia",
    "dent": "dental",
    "med": "médico",
    "clin": "clínico",
    "hosp": "hospitalar",
    "ster": "esterilizado",
    "disp": "descartável",
    "reut": "reutilizável"
}

# Stop words específicas para produtos dentais
STOP_WORDS_DENTAIS = {
    "para", "de", "com", "em", "do", "da", "dos", "das", "um", "uma", "uns", "umas",
    "o", "a", "os", "as", "e", "ou", "se", "que", "por", "até", "desde", "após",
    "dental", "odontológico", "odontologia", "clínico", "profissional", "uso",
    "aplicação", "produto", "material", "instrumento", "equipamento", "sistema",
    "marca", "modelo", "tipo", "cor", "tamanho", "medida", "quantidade", "unidade",
    "registro", "anvisa", "certificado", "iso", "fda", "qualidade", "premium",
    "nacional", "importado", "original", "tradicional", "novo", "melhorado"
}

# Padrões fonéticos (Soundex adaptado para português)
PADROES_FONETICOS = {
    "ph": "f",
    "th": "t", 
    "ch": "x",
    "nh": "n",
    "lh": "l",
    "rr": "r",
    "ss": "s",
    "ç": "s",
    "y": "i",
    "w": "v",
    "k": "c",
    "ck": "c"
}

def expandir_sinonimos(palavra: str) -> list:
    """Expande uma palavra com seus sinônimos"""
    palavra_lower = palavra.lower().strip()
    
    # Verifica se é uma abreviação
    if palavra_lower in ABREVIACOES:
        palavra_expandida = ABREVIACOES[palavra_lower]
        sinonimos = [palavra, palavra_expandida]
        if palavra_expandida in SINONIMOS_PRODUTOS_DENTAIS:
            sinonimos.extend(SINONIMOS_PRODUTOS_DENTAIS[palavra_expandida])
        return list(set(sinonimos))
    
    # Busca sinônimos diretos
    if palavra_lower in SINONIMOS_PRODUTOS_DENTAIS:
        sinonimos = [palavra] + SINONIMOS_PRODUTOS_DENTAIS[palavra_lower]
        return list(set(sinonimos))
    
    return [palavra]

def aplicar_normalizacao_fonetica(texto: str) -> str:
    """Aplica normalização fonética"""
    texto_lower = texto.lower()
    for pattern, replacement in PADROES_FONETICOS.items():
        texto_lower = texto_lower.replace(pattern, replacement)
    return texto_lower

def expandir_texto_com_sinonimos(texto: str) -> str:
    """Expande um texto completo com sinônimos das palavras principais"""
    import re
    
    # Remove pontuação e split em palavras
    palavras = re.findall(r'\b\w+\b', texto.lower())
    
    # Remove stop words
    palavras_filtradas = [p for p in palavras if p not in STOP_WORDS_DENTAIS]
    
    # Expande com sinônimos
    todas_palavras = []
    for palavra in palavras_filtradas:
        todas_palavras.extend(expandir_sinonimos(palavra))
    
    return " ".join(set(todas_palavras))

def calcular_similaridade_semantica(texto1: str, texto2: str) -> float:
    """Calcula similaridade considerando sinônimos"""
    
    # Expande ambos os textos
    expandido1 = set(expandir_texto_com_sinonimos(texto1).split())
    expandido2 = set(expandir_texto_com_sinonimos(texto2).split())
    
    # Calcula interseção e união
    intersecao = len(expandido1 & expandido2)
    uniao = len(expandido1 | expandido2)
    
    if uniao == 0:
        return 0.0
    
    return intersecao / uniao

# Sistema de feedback humano
FEEDBACK_HUMANO = {
    "matches_validados": {},  # id_match: True/False
    "sinonimos_sugeridos": {},  # palavra: [novos_sinonimos]
    "padroes_rejeitados": [],  # padrões que geram falsos positivos
    "melhorias_sugeridas": []  # sugestões textuais
}

def adicionar_feedback(id_match: str, e_match_valido: bool, observacao: str = ""):
    """Adiciona feedback humano ao sistema"""
    FEEDBACK_HUMANO["matches_validados"][id_match] = {
        "valido": e_match_valido,
        "observacao": observacao,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }

def sugerir_sinonimo(palavra_base: str, novo_sinonimo: str):
    """Permite adicionar novos sinônimos baseado em feedback"""
    if palavra_base not in FEEDBACK_HUMANO["sinonimos_sugeridos"]:
        FEEDBACK_HUMANO["sinonimos_sugeridos"][palavra_base] = []
    
    FEEDBACK_HUMANO["sinonimos_sugeridos"][palavra_base].append({
        "sinonimo": novo_sinonimo,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    })

def obter_estatisticas_feedback():
    """Retorna estatísticas do feedback humano"""
    total_feedbacks = len(FEEDBACK_HUMANO["matches_validados"])
    if total_feedbacks == 0:
        return {"total": 0, "precisao": 0, "falsos_positivos": 0}
    
    validos = sum(1 for f in FEEDBACK_HUMANO["matches_validados"].values() if f["valido"])
    falsos_positivos = total_feedbacks - validos
    precisao = (validos / total_feedbacks) * 100
    
    return {
        "total": total_feedbacks,
        "validos": validos,
        "falsos_positivos": falsos_positivos,
        "precisao": precisao,
        "sinonimos_sugeridos": len(FEEDBACK_HUMANO["sinonimos_sugeridos"])
    }

if __name__ == "__main__":
    # Teste do sistema
    print("🧪 TESTANDO SISTEMA DE SINÔNIMOS")
    print("=" * 50)
    
    # Teste de expansão
    palavras_teste = ["resina", "anestésico", "broca", "endo", "comp"]
    for palavra in palavras_teste:
        sinonimos = expandir_sinonimos(palavra)
        print(f"'{palavra}' → {sinonimos}")
    
    print("\nTESTANDO NORMALIZAÇÃO FONÉTICA")
    print("=" * 50)
    textos_teste = ["photopolymer", "technique", "chair", "philosophy"]
    for texto in textos_teste:
        normalizado = aplicar_normalizacao_fonetica(texto)
        print(f"'{texto}' → '{normalizado}'")
    
    print("\nTESTANDO SIMILARIDADE SEMÂNTICA")  
    print("=" * 50)
    pares_teste = [
        ("Resina Composite Z350", "Compósito Fotopolimerizável Z350"),
        ("Anestésico Lidocaína 2%", "Xylocaína 2% com Epinefrina"),
        ("Kit Endodontia", "Conjunto Endo Completo"),
        ("Broca Diamantada", "Fresa Diamond")
    ]
    
    for texto1, texto2 in pares_teste:
        similaridade = calcular_similaridade_semantica(texto1, texto2)
        print(f"'{texto1}' vs '{texto2}' → {similaridade:.2f}")