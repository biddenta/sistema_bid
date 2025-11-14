# Mapeamento: palavra-chave -> (segmento, categoria, subcategoria, peso)
MAPEAMENTOS_ADICIONAIS = {
    # RESINAS (3,114 ocorrências)
    'resina': {
        'composta': ('Dentista', 'Dentística e Estética', 'Resina Composta', 0.95),
        'flow': ('Dentista', 'Dentística e Estética', 'Resina Flow', 0.95),
        'bulk': ('Dentista', 'Dentística e Estética', 'Resina Bulk Fill', 0.95),
        'acrílica': ('Laboratório', 'Resinas e Acrílicos', 'Resina Acrílica', 0.90),
        'bis-acrílica': ('Dentista', 'Prótese', 'Provisórios', 0.90),
        'fotopolimerizável': ('Dentista', 'Dentística e Estética', 'Resina Composta', 0.85),
        'default': ('Dentista', 'Dentística e Estética', 'Resina Composta', 0.70)
    },
    
    # BROCAS (1,183 ocorrências)
    'broca': {
        'carbide': ('Dentista', 'Equipamentos e Peças de Mão', 'Brocas Carbide', 0.95),
        'diamantada': ('Dentista', 'Equipamentos e Peças de Mão', 'Brocas Diamantadas', 0.95),
        'gates': ('Dentista', 'Endodontia', 'Brocas para Endodontia', 0.90),
        'largo': ('Dentista', 'Endodontia', 'Brocas para Endodontia', 0.90),
        'cirúrgica': ('Dentista', 'Cirurgia e Periodontia', 'Brocas Cirúrgicas', 0.90),
        'multilaminada': ('Dentista', 'Equipamentos e Peças de Mão', 'Brocas Multilaminadas', 0.90),
        'default': ('Dentista', 'Equipamentos e Peças de Mão', 'Brocas Diamantadas', 0.60)
    },
    
    # SILICONE (1,086 ocorrências)
    'silicone': {
        'condensação': ('Dentista', 'Materiais de Moldagem e Modelos', 'Silicone de Condensação', 0.95),
        'adição': ('Dentista', 'Materiais de Moldagem e Modelos', 'Silicone de Adição', 0.95),
        'putty': ('Dentista', 'Materiais de Moldagem e Modelos', 'Silicone de Adição', 0.90),
        'moldagem': ('Dentista', 'Materiais de Moldagem e Modelos', 'Silicone de Adição', 0.85),
        'default': ('Dentista', 'Materiais de Moldagem e Modelos', 'Silicone de Adição', 0.70)
    },
    
    # ESCOVA (973 ocorrências)
    'escova': {
        'dental': ('Dentista', 'Prevenção e Profilaxia', 'Escovas Dentais', 0.95),
        'robinson': ('Dentista', 'Prevenção e Profilaxia', 'Escovas de Robinson', 0.95),
        'profilaxia': ('Dentista', 'Prevenção e Profilaxia', 'Escovas para Profilaxia', 0.95),
        'interdental': ('Dentista', 'Prevenção e Profilaxia', 'Escovas Interdentais', 0.95),
        'elétrica': ('Dentista', 'Prevenção e Profilaxia', 'Escovas Elétricas', 0.90),
        'default': ('Dentista', 'Prevenção e Profilaxia', 'Escovas Dentais', 0.70)
    },
    
    # PONTA (1,231 ocorrências)
    'ponta': {
        'diamantada': ('Dentista', 'Equipamentos e Peças de Mão', 'Pontas Diamantadas', 0.95),
        'montada': ('Dentista', 'Equipamentos e Peças de Mão', 'Pontas Montadas', 0.90),
        'polimento': ('Dentista', 'Dentística e Estética', 'Pontas para Polimento', 0.90),
        'silicone': ('Dentista', 'Dentística e Estética', 'Pontas de Silicone', 0.85),
        'default': ('Dentista', 'Equipamentos e Peças de Mão', 'Pontas Diamantadas', 0.60)
    },
    
    # CERÂMICA (851 ocorrências)
    'cerâmica': {
        'feldspática': ('Laboratório', 'Cerâmicas', 'Cerâmica Feldspática', 0.95),
        'zircônia': ('Laboratório', 'Cerâmicas', 'Zircônia', 0.95),
        'dissilicato': ('Laboratório', 'Cerâmicas', 'Dissilicato de Lítio', 0.95),
        'porcelana': ('Laboratório', 'Cerâmicas', 'Porcelana Dental', 0.90),
        'default': ('Laboratório', 'Cerâmicas', 'Cerâmica Feldspática', 0.70)
    },
    
    # ARCO (775 ocorrências)
    'arco': {
        'ortodôntico': ('Dentista', 'Ortodontia', 'Fios Ortodônticos', 0.95),
        'níquel-titânio': ('Dentista', 'Ortodontia', 'Fios Ortodônticos', 0.95),
        'niti': ('Dentista', 'Ortodontia', 'Fios Ortodônticos', 0.95),
        'aço': ('Dentista', 'Ortodontia', 'Fios Ortodônticos', 0.90),
        'termoativado': ('Dentista', 'Ortodontia', 'Fios Ortodônticos', 0.90),
        'default': ('Dentista', 'Ortodontia', 'Fios Ortodônticos', 0.75)
    },
    
    # DISCO (613 ocorrências)
    'disco': {
        'polimento': ('Dentista', 'Dentística e Estética', 'Discos de Polimento', 0.95),
        'lixa': ('Dentista', 'Dentística e Estética', 'Discos de Lixa', 0.90),
        'soflex': ('Dentista', 'Dentística e Estética', 'Discos de Polimento', 0.95),
        'diamantado': ('Dentista', 'Equipamentos e Peças de Mão', 'Discos Diamantados', 0.90),
        'separação': ('Dentista', 'Equipamentos e Peças de Mão', 'Discos de Separação', 0.90),
        'default': ('Dentista', 'Dentística e Estética', 'Discos de Polimento', 0.70)
    },
    
    # TUBO (672 ocorrências)
    'tubo': {
        'ortodôntico': ('Dentista', 'Ortodontia', 'Tubos Ortodônticos', 0.95),
        'molar': ('Dentista', 'Ortodontia', 'Tubos para Molares', 0.95),
        'banda': ('Dentista', 'Ortodontia', 'Bandas e Tubos', 0.90),
        'default': ('Dentista', 'Ortodontia', 'Tubos Ortodônticos', 0.75)
    },
    
    # MOLDEIRA (579 ocorrências)
    'moldeira': {
        'total': ('Dentista', 'Materiais de Moldagem e Modelos', 'Moldeiras', 0.90),
        'parcial': ('Dentista', 'Materiais de Moldagem e Modelos', 'Moldeiras', 0.90),
        'perfurada': ('Dentista', 'Materiais de Moldagem e Modelos', 'Moldeiras', 0.90),
        'clareamento': ('Dentista', 'Dentística e Estética', 'Moldeiras para Clareamento', 0.95),
        'default': ('Dentista', 'Materiais de Moldagem e Modelos', 'Moldeiras', 0.80)
    },
    
    # DENTE (717 ocorrências)
    'dente': {
        'acrílico': ('Laboratório', 'Dentes Artificiais', 'Dentes de Acrílico', 0.95),
        'artificial': ('Laboratório', 'Dentes Artificiais', 'Dentes de Acrílico', 0.95),
        'anterior': ('Laboratório', 'Dentes Artificiais', 'Dentes Anteriores', 0.90),
        'posterior': ('Laboratório', 'Dentes Artificiais', 'Dentes Posteriores', 0.90),
        'default': ('Laboratório', 'Dentes Artificiais', 'Dentes de Acrílico', 0.70)
    },
    
    # LIMA (incluído em padrões mas reforçando)
    'lima': {
        'endodôntica': ('Dentista', 'Endodontia', 'Limas Endodônticas', 0.95),
        'manual': ('Dentista', 'Endodontia', 'Limas Manuais', 0.95),
        'rotatória': ('Dentista', 'Endodontia', 'Limas Rotatórias', 0.95),
        'protaper': ('Dentista', 'Endodontia', 'Limas Rotatórias', 0.95),
        'reciprocante': ('Dentista', 'Endodontia', 'Limas Reciprocantes', 0.95),
        'default': ('Dentista', 'Endodontia', 'Limas Endodônticas', 0.85)
    },
    
    # ADESIVO
    'adesivo': {
        'dental': ('Dentista', 'Dentística e Estética', 'Adesivos Dentais', 0.95),
        'autocondicionante': ('Dentista', 'Dentística e Estética', 'Adesivos Autocondicionantes', 0.95),
        'convencional': ('Dentista', 'Dentística e Estética', 'Adesivos Convencionais', 0.95),
        'universal': ('Dentista', 'Dentística e Estética', 'Adesivos Universais', 0.95),
        'default': ('Dentista', 'Dentística e Estética', 'Adesivos Dentais', 0.80)
    },
    
    # CIMENTO
    'cimento': {
        'ionômero': ('Dentista', 'Cimentos', 'Cimento de Ionômero de Vidro', 0.95),
        'vidro': ('Dentista', 'Cimentos', 'Cimento de Ionômero de Vidro', 0.95),
        'resinoso': ('Dentista', 'Cimentos', 'Cimento Resinoso', 0.95),
        'fosfato': ('Dentista', 'Cimentos', 'Cimento de Fosfato de Zinco', 0.95),
        'zinco': ('Dentista', 'Cimentos', 'Cimento de Fosfato de Zinco', 0.90),
        'provisório': ('Dentista', 'Cimentos', 'Cimento Provisório', 0.90),
        'endodôntico': ('Dentista', 'Endodontia', 'Cimento Endodôntico', 0.95),
        'default': ('Dentista', 'Cimentos', 'Cimento de Ionômero de Vidro', 0.70)
    },
    
    # BANDA (para ortodontia)
    'banda': {
        'ortodôntica': ('Dentista', 'Ortodontia', 'Bandas Ortodônticas', 0.95),
        'molar': ('Dentista', 'Ortodontia', 'Bandas para Molares', 0.95),
        'pré-molar': ('Dentista', 'Ortodontia', 'Bandas Ortodônticas', 0.90),
        'anatomica': ('Dentista', 'Ortodontia', 'Bandas Ortodônticas', 0.90),
        'default': ('Dentista', 'Ortodontia', 'Bandas Ortodônticas', 0.80)
    },
    
    # CLAREAMENTO
    'clareamento': {
        'dental': ('Dentista', 'Dentística e Estética', 'Clareamento Dental', 0.95),
        'peróxido': ('Dentista', 'Dentística e Estética', 'Clareamento Dental', 0.90),
        'gel': ('Dentista', 'Dentística e Estética', 'Clareamento Dental', 0.85),
        'default': ('Dentista', 'Dentística e Estética', 'Clareamento Dental', 0.80)
    },
    
    # PAPEL (toalha, articular, etc)
    'papel': {
        'articular': ('Dentista', 'Outros', 'Papel Carbono e Articular', 0.95),
        'carbono': ('Dentista', 'Outros', 'Papel Carbono e Articular', 0.95),
        'toalha': ('Dentista', 'Descartáveis', 'Papel Toalha', 0.95),
        'grau-cirúrgico': ('Dentista', 'Descartáveis', 'Papel Grau Cirúrgico', 0.95),
        'default': ('Dentista', 'Descartáveis', 'Papel Toalha', 0.70)
    },
    
    # GAZE
    'gaze': {
        'estéril': ('Dentista', 'Descartáveis', 'Gazes', 0.95),
        'não-estéril': ('Dentista', 'Descartáveis', 'Gazes', 0.95),
        'default': ('Dentista', 'Descartáveis', 'Gazes', 0.90)
    },
    
    # LUVA
    'luva': {
        'procedimento': ('Dentista', 'Biossegurança', 'Equipamentos de Proteção Individual (EPIs)', 0.95),
        'cirúrgica': ('Dentista', 'Biossegurança', 'Equipamentos de Proteção Individual (EPIs)', 0.95),
        'látex': ('Dentista', 'Biossegurança', 'Equipamentos de Proteção Individual (EPIs)', 0.90),
        'nitrílica': ('Dentista', 'Biossegurança', 'Equipamentos de Proteção Individual (EPIs)', 0.90),
        'default': ('Dentista', 'Biossegurança', 'Equipamentos de Proteção Individual (EPIs)', 0.90)
    }
}

# Categorias específicas por marca (marcas que indicam categoria específica)
MAPEAMENTO_MARCAS = {
    'morelli': ('Dentista', 'Ortodontia', 'Diversos Ortodontia'),
    'orthometric': ('Dentista', 'Ortodontia', 'Diversos Ortodontia'),
    'american': ('Dentista', 'Ortodontia', 'Diversos Ortodontia'),  # American Orthodontics
    'golgran': ('Dentista', 'Anestésicos e Agulha Gengival', 'Anestésico Injetável'),
    'ivoclar': ('Laboratório', 'Cerâmicas', 'Diversos Cerâmica'),
    'fgm': ('Dentista', 'Dentística e Estética', 'Diversos Estética'),
    'maquira': ('Dentista', 'Equipamentos e Peças de Mão', 'Diversos Equipamentos'),
    'odontomega': ('Dentista', 'Endodontia', 'Diversos Endodontia'),
    'kota': ('Dentista', 'Equipamentos e Peças de Mão', 'Diversos Equipamentos'),
}
