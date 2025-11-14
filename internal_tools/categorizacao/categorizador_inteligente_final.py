import sqlite3
import re
from typing import Dict, Tuple, Optional
from collections import defaultdict
import math

class CategorizadorInteligenteFinal:
    """
    Sistema de categorização com foco em PRECISÃO e CONTEXTO COMPLETO
    """
    
    def __init__(self):
        self.conhecimento = self._carregar_conhecimento()
        self.aprendizado = self._aprender_padroes()
        
    def _carregar_conhecimento(self) -> Dict:
        """Carrega base de conhecimento com regras MUITO mais específicas"""
        return {
            # ==========================================
            # RESINAS - ANÁLISE COMPLETA DO CONTEXTO
            # ==========================================
            'resinas': {
                # Resinas de LABORATÓRIO (3D, protética, acrílica autopolimerizável)
                'laboratorio': [
                    (r'resina.*3d|3d.*resina', 'Solução Digital', 'Resinas para Impressão 3D', 0.95),
                    (r'resina.*impressora|impressora.*resina', 'Solução Digital', 'Resinas para Impressão 3D', 0.95),
                    (r'resina.*calcinável', 'Solução Digital', 'Resinas para Impressão 3D', 0.95),
                    (r'resina.*modelo.*lavável|modelo.*cinza|modelo.*lavável', 'Solução Digital', 'Resinas para Impressão 3D', 0.92),
                    (r'resina acrílica.*autopolimerizável', 'Resinas e Polímeros', 'Resina Acrílica', 0.88),
                    (r'resina acrílica.*(pó|líquido|jet|vipi|onda cryl)', 'Resinas e Polímeros', 'Resina Acrílica', 0.88),
                    (r'resina.*termopolimerizável', 'Resinas e Polímeros', 'Resina Acrílica', 0.88),
                    (r'disco.*resina.*ceramill|resina.*provisória.*disco', 'Resinas e Polímeros', 'Resina Acrílica', 0.85),
                ],
                # Resinas de DENTISTA (composta, flow, bulk fill, estéticas)
                'dentista': [
                    (r'resina.*(composta|composite)', 'Dentística e Estética', 'Resina Composta', 0.95),
                    (r'resina.*(flow|fluida)', 'Dentística e Estética', 'Resina Flow', 0.95),
                    (r'resina.*(bulk|fill)', 'Dentística e Estética', 'Resina Bulk Fill', 0.95),
                    (r'resina.*(charisma|filtek|z350|z250|gradia|opallis|vittra|luna|opus|herculite|tetric|empress|harmonize|natural|color|blend|essentia)', 'Dentística e Estética', 'Resina Composta', 0.92),
                    (r'resina.*(anterior|posterior|universal|micro|nano|híbrida)', 'Dentística e Estética', 'Resina Composta', 0.88),
                    # Genérico - quando não especifica tipo
                    (r'resina(?!.*acrílica|.*3d|.*impressora|.*modelo|.*calcinável)', 'Dentística e Estética', 'Resina Composta', 0.70),
                ]
            },
            
            # ==========================================
            # KITS E COMBOS - PRIORIDADE PELO ITEM PRINCIPAL
            # ==========================================
            'kits': {
                # Se kit tem RESINA COMPOSTA + outros → Dentista
                (r'kit.*(resina composta|resina.*filtek|resina.*charisma|resina.*opallis)', 'Dentista', 'Dentística e Estética', 'Resina Composta', 0.92),
                # Kit de polimento de resina → Dentista
                (r'kit.*(polimento|acabamento).*resina(?!.*acrílico)', 'Dentista', 'Dentística e Estética', 'Instrumentos de Dentística', 0.88),
                # Kit ortodontia
                (r'kit.*(ortodontia|braquete|remoção.*resina.*residual)', 'Dentista', 'Ortodontia', 'Diversos Ortodontia', 0.90),
                # Kit endodontia
                (r'kit.*(endodontia|lima|gates|protaper)', 'Dentista', 'Endodontia', 'Limas Endodônticas', 0.90),
                # Kit laboratório (acrílico, protético)
                (r'kit.*(acrílico|protético|laborató)', 'Laboratório', 'Resinas e Polímeros', 'Resina Acrílica', 0.88),
            },
            
            # ==========================================
            # BROCAS - SEMPRE DENTISTA (exceto laboratoriais explícitas)
            # ==========================================
            'brocas': {
                'dentista': [
                    (r'broca.*(gates|gates-glidden|endo|endodôntica)', 'Endodontia', 'Brocas Endodônticas', 0.95),
                    (r'broca.*(carbide|tungstênio|aço)', 'Equipamentos e Peças de Mão', 'Brocas Cirúrgicas e Burs', 0.90),
                    (r'broca.*(diamantada|ponta diamantada)', 'Equipamentos e Peças de Mão', 'Brocas Cirúrgicas e Burs', 0.90),
                    (r'broca.*(esférica|cônica|cilíndrica|tronco|chama)', 'Equipamentos e Peças de Mão', 'Brocas Cirúrgicas e Burs', 0.88),
                    (r'broca', 'Equipamentos e Peças de Mão', 'Brocas Cirúrgicas e Burs', 0.75),
                ],
                'laboratorio': [
                    (r'broca.*(polimento de acrílico|acrílico)', 'Materiais para Acabamento e Polimento', 'Brocas e Fresas Laboratoriais', 0.88),
                ]
            },
            
            # ==========================================
            # LIMAS - SEMPRE ENDODONTIA (exceto estojos)
            # ==========================================
            'limas': {
                (r'lima.*(protaper|reciproc|pathfile|mtwo|twisted|hyflex|one shape|wave one)', 'Dentista', 'Endodontia', 'Limas Endodônticas', 0.95),
                (r'lima.*(k-file|hedstroem|kerr|manual|rotatória|endodôntica)', 'Dentista', 'Endodontia', 'Limas Endodônticas', 0.92),
                (r'estojo.*lima', 'Laboratório', 'Instrumentos e Ferramentas', 'Organizadores e Estojos', 0.88),
                (r'lima', 'Dentista', 'Endodontia', 'Limas Endodônticas', 0.85),
            },
            
            # ==========================================
            # ADESIVOS - SEMPRE DENTISTA
            # ==========================================
            'adesivos': {
                (r'adesivo.*(single bond|scotchbond|prime & bond|optibond|clearfil|ambar|stae|magic bond)', 'Dentista', 'Dentística e Estética', 'Adesivos e Primers', 0.95),
                (r'adesivo.*(dentário|dental|universal|autocondicionante)', 'Dentista', 'Dentística e Estética', 'Adesivos e Primers', 0.92),
                (r'adesivo', 'Dentista', 'Dentística e Estética', 'Adesivos e Primers', 0.85),
            },
            
            # ==========================================
            # CIMENTOS - ANALISAR TIPO
            # ==========================================
            'cimentos': {
                (r'cimento.*(resinoso|dual|autoadesivo|nx3|panavia|relyx|variolink|allcem)', 'Dentista', 'Cimentos', 'Cimentos Resinosos', 0.95),
                (r'cimento.*(ionômero|ionomérico|ketac|vidrion|maxxion)', 'Dentista', 'Cimentos', 'Cimentos de Ionômero de Vidro', 0.95),
                (r'cimento.*(endodôntico|sealer|ah plus|endofill|sealapex)', 'Dentista', 'Cimentos', 'Cimentos Endodônticos', 0.95),
                (r'cimento.*(provisório|temp bond|rely x temp)', 'Dentista', 'Cimentos', 'Cimentos Provisórios', 0.92),
                (r'cimento.*(fosfato|zinco)', 'Dentista', 'Cimentos', 'Cimentos de Fosfato de Zinco', 0.90),
            },
            
            # ==========================================
            # ANESTÉSICOS - SEMPRE DENTISTA
            # ==========================================
            'anestesicos': {
                (r'anestésico.*(tópico|spray|gel)', 'Dentista', 'Anestésicos e Agulha Gengival', 'Anestésico Tópico', 0.95),
                (r'anestésico.*(lidocaína|mepivacaína|prilocaína|articaína|bupivacaína)', 'Dentista', 'Anestésicos e Agulha Gengival', 'Anestésico Injetável', 0.95),
                (r'aquecedor.*anestésico', 'Dentista', 'Anestésicos e Agulha Gengival', 'Anestésico Injetável', 0.88),
                (r'anestésico', 'Dentista', 'Anestésicos e Agulha Gengival', 'Anestésico Injetável', 0.90),
            },
            
            # ==========================================
            # CLAREAMENTO - SEMPRE DENTISTA
            # ==========================================
            'clareamento': {
                (r'clareamento|clareador|whiteness|opalescence|pola', 'Dentista', 'Dentística e Estética', 'Clareamento Dental', 0.95),
                (r'ponteira.*clareamento', 'Dentista', 'Equipamentos e Peças de Mão', 'Acessórios para Equipamentos', 0.88),
            },
            
            # ==========================================
            # SILICONES - ANALISAR TIPO
            # ==========================================
            'silicones': {
                (r'silicone.*(adição|condensação|express|putty|light|heavy|regular)', 'Dentista', 'Moldagem', 'Silicones de Adição/Condensação', 0.95),
                (r'silicone.*moldagem', 'Dentista', 'Moldagem', 'Silicones de Adição/Condensação', 0.95),
                (r'silicone.*(laboratorial|duplicação|molde)', 'Laboratório', 'Resinas e Polímeros', 'Silicones Laboratoriais', 0.90),
            },
            
            # ==========================================
            # MARCAS ESPECÍFICAS - OVERRIDE DE CATEGORIA
            # ==========================================
            'marcas': {
                'morelli': ('Dentista', 'Ortodontia', 'Diversos Ortodontia', 0.85),
                'orthometric': ('Dentista', 'Ortodontia', 'Diversos Ortodontia', 0.85),
                'golgran': ('Dentista', 'Anestésicos e Agulha Gengival', 'Anestésico Injetável', 0.85),
                'kulzer': ('Dentista', 'Dentística e Estética', 'Resina Composta', 0.75),  # Charisma
                'dentsply': ('Dentista', 'Endodontia', 'Limas Endodônticas', 0.75),  # Protaper
            },
            
            # ==========================================
            # BIOSSEGURANÇA - SEMPRE DENTISTA
            # ==========================================
            'biosseguranca': {
                # EPIs
                (r'luva|glove', 'Dentista', 'Biossegurança', 'Equipamentos de Proteção Individual (EPIs)', 0.95),
                (r'máscara|mask', 'Dentista', 'Biossegurança', 'Equipamentos de Proteção Individual (EPIs)', 0.95),
                (r'jaleco|avental', 'Dentista', 'Biossegurança', 'Equipamentos de Proteção Individual (EPIs)', 0.95),
                (r'gorro|touca', 'Dentista', 'Biossegurança', 'Equipamentos de Proteção Individual (EPIs)', 0.95),
                
                # Descartáveis e Consumíveis
                (r'sugador.*descartável|sugador.*transparente|sugador.*flex', 'Dentista', 'Biossegurança', 'Descartáveis e Consumíveis', 0.92),
                (r'gaze|compressa.*gaze|atadura', 'Dentista', 'Biossegurança', 'Descartáveis e Consumíveis', 0.92),
                (r'algodão.*rolete|algodão.*hidrófilo|algodão ortopédico', 'Dentista', 'Biossegurança', 'Descartáveis e Consumíveis', 0.88),
                
                # Controle de Esterilização
                (r'indicador.*químico|indicador.*biológico|indicador.*classe', 'Dentista', 'Biossegurança', 'Controle de Esterilização', 0.95),
                (r'envelope.*esterilização|envelope.*autosselante', 'Dentista', 'Biossegurança', 'Controle de Esterilização', 0.95),
                (r'fita.*autoclave|fita.*esterilização', 'Dentista', 'Biossegurança', 'Controle de Esterilização', 0.92),
                (r'rolo.*esterilização|grau cirúrgico', 'Dentista', 'Biossegurança', 'Controle de Esterilização', 0.92),
                (r'papel.*crepado.*esterilização', 'Dentista', 'Biossegurança', 'Controle de Esterilização', 0.92),
                
                # Desinfecção e Limpeza
                (r'desinfetante|desinfecção|germicida', 'Dentista', 'Biossegurança', 'Desinfecção e Limpeza', 0.95),
                (r'álcool.*70|álcool gel|álcool líquido', 'Dentista', 'Biossegurança', 'Desinfecção e Limpeza', 0.95),
                (r'hipoclorito.*sódio|soda clorada', 'Dentista', 'Biossegurança', 'Desinfecção e Limpeza', 0.95),
                (r'glutaraldeído', 'Dentista', 'Biossegurança', 'Desinfecção e Limpeza', 0.95),
                (r'sabonete.*antisséptico|sabonete.*líquido.*mãos', 'Dentista', 'Biossegurança', 'Desinfecção e Limpeza', 0.90),
            },
            
            # ==========================================
            # INSTRUMENTAIS CIRÚRGICOS E CLÍNICOS
            # ==========================================
            'instrumentais': {
                # Cirurgia e Periodontia
                (r'pinça.*hemostática|pinça.*kelly|pinça.*halsted', 'Dentista', 'Cirurgia e Periodontia', 'Acessórios para Cirurgia e Periodontia', 0.95),
                (r'pinça.*dente|pinça.*raiz|pinça.*extração', 'Dentista', 'Cirurgia e Periodontia', 'Acessórios para Cirurgia e Periodontia', 0.95),
                (r'tesoura.*íris|tesoura.*metzenbaum|tesoura.*cirúrgica', 'Dentista', 'Cirurgia e Periodontia', 'Acessórios para Cirurgia e Periodontia', 0.95),
                (r'porta.*agulha.*mayo|porta.*agulha.*castroviejo', 'Dentista', 'Cirurgia e Periodontia', 'Acessórios para Cirurgia e Periodontia', 0.95),
                (r'cabo.*bisturi|lâmina.*bisturi', 'Dentista', 'Cirurgia e Periodontia', 'Acessórios para Cirurgia e Periodontia', 0.95),
                (r'afastador.*minnesota|afastador.*farabeuf|afastador.*cirúrgico', 'Dentista', 'Cirurgia e Periodontia', 'Acessórios para Cirurgia e Periodontia', 0.92),
                (r'cureta.*perio|cureta.*gracey|cureta.*lucas|cureta.*mccall', 'Dentista', 'Cirurgia e Periodontia', 'Acessórios para Cirurgia e Periodontia', 0.95),
                
                # Instrumentais Clínicos
                (r'sonda.*exploradora|sonda.*clínica|sonda.*oms', 'Dentista', 'Equipamentos e Peças de Mão', 'Equipamentos para Consultório', 0.92),
                (r'espelho.*bucal|cabo.*espelho', 'Dentista', 'Equipamentos e Peças de Mão', 'Equipamentos para Consultório', 0.92),
                (r'pinça.*clínica.*algodão|porta.*algodão', 'Dentista', 'Equipamentos e Peças de Mão', 'Equipamentos para Consultório', 0.88),
                (r'espátula.*inserção|espátula.*resina|espátula.*compósita', 'Dentista', 'Dentística e Estética', 'Instrumentos de Dentística', 0.90),
                
                # Cubas e Bandejas
                (r'cuba.*inox|cuba.*assepsia|cuba.*redonda', 'Dentista', 'Equipamentos e Peças de Mão', 'Equipamentos para Consultório', 0.88),
                (r'bandeja.*esterilização|bandeja.*inox|bandeja.*cirúrgica', 'Dentista', 'Equipamentos e Peças de Mão', 'Equipamentos para Consultório', 0.88),
                (r'pote.*dappen|pote.*paladon', 'Dentista', 'Equipamentos e Peças de Mão', 'Equipamentos para Consultório', 0.88),
            },
            
            # ==========================================
            # PAPEL - DIFERENTES TIPOS
            # ==========================================
            'papel': {
                # Endodontia
                (r'ponta.*papel|papel.*absorvente.*endo|cone.*papel', 'Dentista', 'Endodontia', 'Acessórios para Endodontia', 0.95),
                
                # Articulação (Cirurgia)
                (r'papel.*carbono|papel.*articulação|carbono.*oclusão', 'Dentista', 'Cirurgia e Periodontia', 'Acessórios para Cirurgia e Periodontia', 0.92),
                
                # Esterilização (Biossegurança) - já coberto em biosseguranca
                
                # Papel para radiografia
                (r'papel.*filme.*raio', 'Radiologia', 'Imagem e Radiologia', 'Acessórios para Radiologia', 0.88),
            },
            
            # ==========================================
            # MOLDAGEM
            # ==========================================
            'moldagem': {
                (r'moldeira.*total|moldeira.*parcial|moldeira.*metal|moldeira.*plástico', 'Dentista', 'Moldagem', 'Moldeiras e Acessórios', 0.95),
                (r'moldeira.*clareamento|placa.*moldeira.*clareamento', 'Dentista', 'Dentística e Estética', 'Clareamento Dental', 0.92),
                (r'moldeira.*flúor', 'Dentista', 'Prevenção e Profilaxia', 'Equipamentos para Profilaxia', 0.92),
                (r'transfer.*moldeira|moldeira.*implante', 'Dentista', 'Implantodontia', 'Instrumentais para Implantodontia', 0.92),
            },
            
            # ==========================================
            # RADIOLOGIA E IMAGEM
            # ==========================================
            'radiologia': {
                (r'revelador.*radiográfico|revelador.*raio', 'Radiologia', 'Imagem e Radiologia', 'Acessórios para Radiologia', 0.95),
                (r'fixador.*radiográfico|fixador.*raio', 'Radiologia', 'Imagem e Radiologia', 'Acessórios para Radiologia', 0.95),
                (r'filme.*radiográfico|filme.*raio.*x', 'Radiologia', 'Imagem e Radiologia', 'Acessórios para Radiologia', 0.95),
                (r'posicionador.*radiográfico|posicionador.*filme', 'Radiologia', 'Imagem e Radiologia', 'Acessórios para Radiologia', 0.92),
                (r'sensor.*radiografia.*digital', 'Radiologia', 'Imagem e Radiologia', 'Acessórios para Radiologia', 0.95),
                (r'afastador.*labial.*expandex|afastador.*raio.*x', 'Radiologia', 'Imagem e Radiologia', 'Acessórios para Radiologia', 0.88),
            },
            
            # ==========================================
            # ISOLAMENTO E GRAMPOS
            # ==========================================
            'isolamento': {
                (r'lençol.*borracha|dique.*borracha|isolamento.*absoluto', 'Dentista', 'Equipamentos e Peças de Mão', 'Equipamentos para Consultório', 0.92),
                (r'grampo.*isolamento|clamp.*isolamento', 'Dentista', 'Equipamentos e Peças de Mão', 'Equipamentos para Consultório', 0.92),
                (r'grampo(?!.*ortodont)', 'Dentista', 'Equipamentos e Peças de Mão', 'Equipamentos para Consultório', 0.85),
            },
            
            # ==========================================
            # ALGINATO E MOLDAGEM
            # ==========================================
            'alginato': {
                (r'alginato', 'Dentista', 'Moldagem', 'Materiais de Moldagem', 0.95),
                (r'godiva', 'Dentista', 'Moldagem', 'Materiais de Moldagem', 0.95),
                (r'pasta.*zinco.*eugenol|pasta.*óxido', 'Dentista', 'Moldagem', 'Materiais de Moldagem', 0.90),
            },
            
            # ==========================================
            # CONSUMÍVEIS DESCARTÁVEIS
            # ==========================================
            'consumiveis_descartaveis': {
                (r'campo.*mesa.*auxiliar', 'Dentista', 'Biossegurança', 'Descartáveis e Consumíveis', 0.92),
                (r'abaixador.*língua|espátula.*madeira', 'Dentista', 'Biossegurança', 'Descartáveis e Consumíveis', 0.90),
            },
            
            # ==========================================
            # MATERIAIS DE LABORATÓRIO
            # ==========================================
            'materiais_laboratorio': {
                (r'revestimento.*cerâmica|gilvest|bellavest|rematitan|heat.*shock', 'Laboratório', 'Instrumentos e Ferramentas', 'Espátulas e Instrumentos para Gesso', 0.95),
                (r'troquel|troquelizador', 'Laboratório', 'Instrumentos e Ferramentas', 'Espátulas e Instrumentos para Gesso', 0.95),
                (r'vaselina.*sólida|separador|isolante.*gesso', 'Laboratório', 'Instrumentos e Ferramentas', 'Espátulas e Instrumentos para Gesso', 0.90),
                (r'cera.*fundição|cera.*carving', 'Laboratório', 'Instrumentos e Ferramentas', 'Espátulas e Instrumentos para Gesso', 0.90),
            },
            
            # ==========================================
            # ACRÍLICO ORTODÔNTICO
            # ==========================================
            'acrilico_ortodontico': {
                (r'acrílico.*ortodôntico|orto.*clas|acrilico.*ortodont', 'Laboratório', 'Resinas e Polímeros', 'Resinas Acrílicas', 0.95),
            },
            
            # ==========================================
            # ANTISSÉPTICOS E DEGERMANTES (REFORÇO)
            # ==========================================
            'antissepticos_reforco': {
                (r'clorexidina|riohex|digluconato', 'Dentista', 'Biossegurança', 'Desinfecção e Limpeza', 0.95),
                (r'álcool.*etílico|rialcool|alcool.*70', 'Dentista', 'Biossegurança', 'Desinfecção e Limpeza', 0.95),
                (r'degermante|antisséptico.*tópico', 'Dentista', 'Biossegurança', 'Desinfecção e Limpeza', 0.95),
                (r'detergente.*enzimático|riozyme', 'Dentista', 'Biossegurança', 'Desinfecção e Limpeza', 0.95),
            },
            
            # ==========================================
            # ORTODONTIA
            # ==========================================
            'ortodontia': {
                (r'braquete|bracket', 'Dentista', 'Ortodontia', 'Bráquetes', 0.95),
                (r'arco.*niti|arco.*aço|arco ortodôntico', 'Dentista', 'Ortodontia', 'Fios e Arcos Ortodônticos', 0.95),
                (r'banda.*ortodôntica', 'Dentista', 'Ortodontia', 'Bandas Ortodônticas', 0.95),
                (r'elástico.*ortodôntico', 'Dentista', 'Ortodontia', 'Elásticos Ortodônticos', 0.92),
                (r'posicionador.*braquete', 'Dentista', 'Ortodontia', 'Diversos Ortodontia', 0.90),
            },
            
            # ==========================================
            # ESCOVA E PREVENÇÃO
            # ==========================================
            'prevencao': {
                (r'escova.*(dental|interdental|profilática)', 'Dentista', 'Prevenção e Profilaxia', 'Escovas e Taças de Profilaxia', 0.95),
                (r'pasta.*profiláti', 'Dentista', 'Prevenção e Profilaxia', 'Pastas Profiláticas', 0.95),
                (r'fio dental|fita dental', 'Dentista', 'Prevenção e Profilaxia', 'Fios e Fitas Dentais', 0.95),
            },
            
            # ==========================================
            # CERÂMICAS E PORCELANAS - LABORATÓRIO
            # ==========================================
            'ceramicas': {
                (r'cerâmica|porcelana|zircônia|dissilicato|emax|ips.*empress', 'Laboratório', 'Dentes Artificiais', 'Dentes de Porcelana/Cerâmica', 0.95),
                (r'disco.*zircônia|bloco.*cerâmica', 'Laboratório', 'Solução Digital', 'Blocos e Discos para CAD/CAM', 0.92),
            },
        }
    
    def _aprender_padroes(self) -> Dict:
        """Aprende padrões de produtos BEM categorizados"""
        conn = sqlite3.connect('match_crew.db')
        cursor = conn.cursor()
        
        # Buscar produtos BEM categorizados (não em "Outros")
        cursor.execute("""
            SELECT nome, marca, segmento, categoria, subcategoria
            FROM produtos
            WHERE categoria != 'Outros' AND categoria IS NOT NULL
            LIMIT 15000
        """)
        
        # Construir vocabulário por categoria
        vocabulario = defaultdict(lambda: defaultdict(int))
        contagem_categoria = defaultdict(int)
        
        for nome, marca, seg, cat, subcat in cursor.fetchall():
            if not nome:
                continue
                
            chave_cat = f"{seg}|{cat}|{subcat}"
            contagem_categoria[chave_cat] += 1
            
            # Extrair palavras significativas
            palavras = self._extrair_palavras(nome)
            for palavra in palavras:
                vocabulario[chave_cat][palavra] += 1
        
        conn.close()
        
        # Calcular TF-IDF simplificado
        aprendizado = {}
        for chave_cat, palavras in vocabulario.items():
            if contagem_categoria[chave_cat] < 5:  # Mínimo 5 exemplos
                continue
                
            # Palavras mais discriminativas
            palavras_importantes = sorted(
                palavras.items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]
            
            aprendizado[chave_cat] = {
                'palavras': dict(palavras_importantes),
                'total': contagem_categoria[chave_cat]
            }
        
        return aprendizado
    
    def _extrair_palavras(self, texto: str) -> set:
        """Extrai palavras significativas do texto"""
        if not texto:
            return set()
            
        texto = texto.lower()
        
        # Remover stopwords muito comuns
        stopwords = {'de', 'para', 'com', 'sem', 'em', 'kit', 'unidades', 'mm', 'cx', 'ref'}
        
        # Extrair palavras
        palavras = re.findall(r'\b\w+\b', texto)
        palavras = [p for p in palavras if len(p) > 2 and p not in stopwords]
        
        return set(palavras)
    
    def categorizar(self, nome: str, marca: str = '') -> Tuple[str, str, str, float]:
        """
        Categoriza um produto com MÁXIMA PRECISÃO
        
        Returns: (segmento, categoria, subcategoria, confianca)
        """
        if not nome:
            return ('Dentista', 'Outros', 'Não Classificado', 0.0)
        
        nome_lower = nome.lower()
        marca_lower = marca.lower() if marca else ''
        
        melhor_resultado = None
        melhor_confianca = 0.0
        
        # ========================================
        # ETAPA 1: REGRAS ESPECÍFICAS (PRIORIDADE MÁXIMA)
        # ========================================
        
        # RESINAS - análise completa
        if 'resina' in nome_lower:
            # Laboratório primeiro (mais específico)
            for padrao, cat, subcat, conf in self.conhecimento['resinas']['laboratorio']:
                if re.search(padrao, nome_lower):
                    return ('Laboratório', cat, subcat, conf)
            
            # Depois Dentista
            for padrao, cat, subcat, conf in self.conhecimento['resinas']['dentista']:
                if re.search(padrao, nome_lower):
                    return ('Dentista', cat, subcat, conf)
        
        # KITS - prioridade pelo item principal
        if 'kit' in nome_lower:
            for padrao, seg, cat, subcat, conf in self.conhecimento['kits']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # BROCAS
        if 'broca' in nome_lower:
            # Laboratório primeiro
            for padrao, cat, subcat, conf in self.conhecimento['brocas'].get('laboratorio', []):
                if re.search(padrao, nome_lower):
                    return ('Laboratório', cat, subcat, conf)
            # Depois Dentista
            for padrao, cat, subcat, conf in self.conhecimento['brocas']['dentista']:
                if re.search(padrao, nome_lower):
                    return ('Dentista', cat, subcat, conf)
        
        # LIMAS
        if 'lima' in nome_lower:
            for padrao, seg, cat, subcat, conf in self.conhecimento['limas']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # ADESIVOS
        if 'adesivo' in nome_lower:
            for padrao, seg, cat, subcat, conf in self.conhecimento['adesivos']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # CIMENTOS
        if 'cimento' in nome_lower:
            for padrao, seg, cat, subcat, conf in self.conhecimento['cimentos']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # ANESTÉSICOS
        if 'anestésico' in nome_lower or 'anestesico' in nome_lower:
            for padrao, seg, cat, subcat, conf in self.conhecimento['anestesicos']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # CLAREAMENTO
        if 'clareamento' in nome_lower or 'clareador' in nome_lower:
            for padrao, seg, cat, subcat, conf in self.conhecimento['clareamento']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # SILICONES
        if 'silicone' in nome_lower:
            for padrao, seg, cat, subcat, conf in self.conhecimento['silicones']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # ALGINATO E MOLDAGEM
        if 'alginato' in nome_lower or 'godiva' in nome_lower:
            for padrao, seg, cat, subcat, conf in self.conhecimento['alginato']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # ISOLAMENTO E GRAMPOS
        if 'lençol' in nome_lower or 'borracha' in nome_lower or 'grampo' in nome_lower or 'dique' in nome_lower:
            for padrao, seg, cat, subcat, conf in self.conhecimento['isolamento']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # MATERIAIS DE LABORATÓRIO
        if any(palavra in nome_lower for palavra in ['revestimento', 'troquel', 'vaselina', 'gilvest', 'bellavest']):
            for padrao, seg, cat, subcat, conf in self.conhecimento['materiais_laboratorio']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # ACRÍLICO ORTODÔNTICO
        if 'acrílico' in nome_lower or 'acrilico' in nome_lower:
            for padrao, seg, cat, subcat, conf in self.conhecimento['acrilico_ortodontico']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # ANTISSÉPTICOS E DEGERMANTES (REFORÇO)
        if any(palavra in nome_lower for palavra in ['clorexidina', 'riohex', 'degermante', 'detergente', 'riozyme']):
            for padrao, seg, cat, subcat, conf in self.conhecimento['antissepticos_reforco']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # CONSUMÍVEIS DESCARTÁVEIS
        if 'campo' in nome_lower or 'abaixador' in nome_lower:
            for padrao, seg, cat, subcat, conf in self.conhecimento['consumiveis_descartaveis']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # PAPEL - diferentes contextos
        if 'papel' in nome_lower or 'carbono' in nome_lower:
            for padrao, seg, cat, subcat, conf in self.conhecimento['papel']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # MOLDAGEM
        if 'moldeira' in nome_lower:
            for padrao, seg, cat, subcat, conf in self.conhecimento['moldagem']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # RADIOLOGIA
        if any(palavra in nome_lower for palavra in ['revelador', 'fixador', 'filme', 'sensor', 'posicionador']):
            for padrao, seg, cat, subcat, conf in self.conhecimento['radiologia']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # INSTRUMENTAIS
        if any(palavra in nome_lower for palavra in ['pinça', 'tesoura', 'porta', 'cabo', 'sonda', 'espelho', 'cureta', 'afastador', 'espátula', 'cuba', 'bandeja', 'pote']):
            for padrao, seg, cat, subcat, conf in self.conhecimento['instrumentais']:
                if re.search(padrao, nome_lower):
                    return (seg, cat, subcat, conf)
        
        # BIOSSEGURANÇA (DEVE VIR DEPOIS DOS INSTRUMENTAIS)
        for padrao, seg, cat, subcat, conf in self.conhecimento['biosseguranca']:
            if re.search(padrao, nome_lower):
                return (seg, cat, subcat, conf)
        
        # ORTODONTIA
        for padrao, seg, cat, subcat, conf in self.conhecimento['ortodontia']:
            if re.search(padrao, nome_lower):
                return (seg, cat, subcat, conf)
        
        # PREVENÇÃO
        for padrao, seg, cat, subcat, conf in self.conhecimento['prevencao']:
            if re.search(padrao, nome_lower):
                return (seg, cat, subcat, conf)
        
        # CERÂMICAS
        for padrao, seg, cat, subcat, conf in self.conhecimento['ceramicas']:
            if re.search(padrao, nome_lower):
                return (seg, cat, subcat, conf)
        
        # ========================================
        # ETAPA 2: MARCAS ESPECÍFICAS
        # ========================================
        if marca_lower:
            for marca_key, (seg, cat, subcat, conf) in self.conhecimento['marcas'].items():
                if marca_key in marca_lower:
                    if melhor_confianca < conf:
                        melhor_resultado = (seg, cat, subcat)
                        melhor_confianca = conf
        
        # ========================================
        # ETAPA 3: APRENDIZADO DE PADRÕES
        # ========================================
        palavras_produto = self._extrair_palavras(nome)
        
        for chave_cat, dados in self.aprendizado.items():
            seg, cat, subcat = chave_cat.split('|')
            
            # Calcular score de similaridade
            palavras_categoria = dados['palavras']
            matches = sum(palavras_categoria.get(p, 0) for p in palavras_produto)
            
            if matches > 0:
                # Normalizar pelo total de produtos na categoria
                score = min(matches / 10.0, 1.0) * 0.65  # Max 65% de confiança
                
                if score > melhor_confianca:
                    melhor_resultado = (seg, cat, subcat)
                    melhor_confianca = score
        
        # ========================================
        # RETORNO
        # ========================================
        if melhor_resultado and melhor_confianca >= 0.30:
            return (*melhor_resultado, melhor_confianca)
        
        # Fallback
        return ('Dentista', 'Outros', 'Não Classificado', 0.0)


# ===================================
# TESTE RÁPIDO
# ===================================
if __name__ == "__main__":
    categorizador = CategorizadorInteligenteFinal()
    
    casos_teste = [
        # Resinas
        ("Resina Charisma Classic Esmalte A1", "Kulzer"),
        ("Resina Acrílica Autopolimerizável Jet", "Clássico"),
        # Kits e Adesivos
        ("Kit Resina Filtek + Adesivo Single Bond", "3M"),
        ("Adesivo Single Bond Universal", "3M"),
        # Endodontia
        ("Broca Gates-Glidden #2", "Dentsply"),
        ("Lima Protaper Next X1", "Dentsply"),
        ("Ponta de Papel Absorvente 25mm", "Dentsply"),
        # Cimentos
        ("Cimento Resinoso Nx3", "Kerr"),
        # Biossegurança - NOVOS CASOS
        ("Sugador Descartável Transparente", "AllPrime"),
        ("Indicador Químico Integrador Classe 5", "Cristófoli"),
        ("Indicador Biológico 24 horas", "2I"),
        ("Compressa de Gaze 11 Fios Estéril", "Cremer"),
        ("Algodão Rolete Nº 2", "Cremer"),
        ("Envelope Autosselante 90x260mm", "Amcor"),
        ("Fita para Autoclave", "Cremer"),
        ("Desinfetante Germicidal", "Asfer"),
        ("Hipoclorito de Sódio 2,5%", "Asfer"),
        # Instrumentais - NOVOS CASOS
        ("Pinça Hemostática Kelly", "Golgran"),
        ("Tesoura Íris Curva", "Golgran"),
        ("Sonda Exploradora Oitavada", "Golgran"),
        ("Espelho Bucal Nº 5", "Ice"),
        ("Cureta Perio Gracey", "Hu-Friedy"),
        ("Espátula Para Resina Nº 2", "Fava"),
        # Papel - NOVOS CASOS
        ("Papel Carbono Contacto Paper", "Angelus"),
        # Moldeiras - NOVOS CASOS
        ("Moldeira Total Perfurada Adulto", "Angelus"),
        ("Moldeira Dupla para Flúor", "AF do Brasil"),
        # Radiologia - NOVOS CASOS
        ("Revelador Radiográfico", "AF do Brasil"),
        ("Filme Radiográfico E-Speed", "AllPrime"),
        ("Posicionador Radiográfico Cone", "Maquira"),
        # Ortodontia
        ("Braquete Metálico Roth 022", "Morelli"),
        # Prevenção
        ("Escova Interdental", "TePe"),
        # NOVOS - Isolamento
        ("Lençol de Borracha Isolamento Médio 15cm", "Madeitex"),
        ("Grampo para Isolamento 212", "Hu-Friedy"),
        # NOVOS - Alginato
        ("Alginato Cavex Cream 500g", "Cavex"),
        ("Godiva em Bastão", "Kerr"),
        # NOVOS - Consumíveis
        ("Campo de Mesa Auxiliar 70x90", "Medis"),
        ("Abaixador de Língua Madeira 100un", "Estilo"),
        # NOVOS - Materiais Lab
        ("Revestimento Gilvest HS", "Bradent"),
        ("Vaselina Sólida 90g", "Rioquímica"),
        ("Troquelizador Bafix", "Labordental"),
        # NOVOS - Acrílico Ortodôntico
        ("Acrílico Ortodôntico Orto Clas 1000g", "Clássico"),
        # NOVOS - Antissépticos Reforço
        ("Clorexidina Riohex 2% 1L", "Rioquímica"),
        ("Detergente Enzimático Riozyme", "Rioquímica"),
    ]
    
    print("=" * 100)
    print("TESTE DO CATEGORIZADOR INTELIGENTE FINAL")
    print("=" * 100)
    
    for nome, marca in casos_teste:
        seg, cat, subcat, conf = categorizador.categorizar(nome, marca)
        print(f"\n{nome[:60]:60}")
        print(f"  → {seg} > {cat} > {subcat}")
        print(f"  → Confiança: {conf*100:.0f}%")
