"""
Trakya Dialect Service - Turkish Thrace Dialect Processing
Converts standard Turkish to Trakya dialect and handles bilingual responses
Enhanced with advanced Turkish language intelligence
"""

import re
import logging
import random
from typing import Dict, List, Optional, Tuple, Any

# Import enhanced services
enhanced_turkish_service = None
enhanced_english_service = None

try:
    from .enhanced_turkish_service import EnhancedTurkishService
    enhanced_turkish_service = EnhancedTurkishService()
except ImportError:
    try:
        from enhanced_turkish_service import EnhancedTurkishService
        enhanced_turkish_service = EnhancedTurkishService()
    except ImportError:
        pass

try:
    from .enhanced_english_service import EnhancedEnglishService
    enhanced_english_service = EnhancedEnglishService()
except ImportError:
    try:
        from enhanced_english_service import EnhancedEnglishService
        enhanced_english_service = EnhancedEnglishService()
    except ImportError:
        pass

logger = logging.getLogger(__name__)

class TrakyaDialectService:
    """
    Service for converting text to Trakya (Thrace) dialect
    Handles phonetic changes, vocabulary, and regional expressions
    """
    
    def __init__(self):
        # User behavior tracking for aggression levels
        self.user_curse_count = 0
        self.user_last_message_type = "normal"  # normal, curse, threat
        self.aggression_threshold = 2  # After 2 curses, become defensive
        self.conversation_turn_count = 0
        
        # TRAKYA DIALECT - SELECTIVE PHONETIC WORDS (only most characteristic)
        # Phonetic substitutions (o -> u pattern) - SELECTIVE USE ONLY
        self.o_to_u_words = {
            "olur": "ulur",     # Keep this - very characteristic
            "olmaz": "ulmaz",   # Keep this - very characteristic
            "oldu": "uldu",     # Keep this - very characteristic
            # Remove most others to avoid overuse
            "doktor": "duktur", # Keep this one - it's classic
        }
        
        # H-dropping patterns (initial H removal) - MASSIVELY EXPANDED
        self.h_drop_words = {
            "hastane": "astane",
            "hayır": "ayır", 
            "hasan": "asan",
            "hülya": "ülya",
            "hakkı": "akı",
            "hüseyin": "üseyin",
            "hemen": "emen",
            "hiç": "iç",
            "her": "er",
            "hoş": "oş",
            "hava": "ava",
            "haber": "aber",
            "hasta": "asta",
            "hikaye": "ikaye",
            "hatırlıyor": "atırlıyor",
            "herkes": "erkes",
            "hepsini": "epsini",
            "herşey": "erşey",
            "hala": "ala",
            "hangi": "angi",
            "hanım": "anım",
            "harika": "arika",
            "hazır": "azır",
            "hesap": "esap",
            "hızlı": "ızlı",
            "hoşça": "oşça",
            "hükmü": "ükmü",
            "hürmet": "ürmet",
            "hürriyet": "ürriyet"
        }
        
        # Regional vocabulary - MASSIVE EXPANSION (70+ WORDS)
        self.regional_vocab = {
            "çocuk": "kızan",
            "çocuklar": "kızanlar", 
            "çocuğun": "kızanın",
            "çocukluk": "kızanlık",
            "tamamen": "epten",
            "hepten": "epten",
            "ayçiçeği": "gündöndü",
            "domates": "dumatis",
            "biraz": "bikerette",
            "hemen": "maacır",
            "kırpmak": "pırkalamak",
            "sıkıştırmak": "sıpıtmak",
            "araştırmak": "aydamak",
            "güneş": "gündendi",
            "sonra": "sefte",
            "yemek": "somak",
            "aptal": "alık",
            "konuşmak": "şakıtmak",
            "güzel": "gamzel",
            "üzerine": "üste",
            "küçük": "küçün",
            "buğday": "buday",
            "pancar": "pancarız",
            "kapak": "kapçık",
            "küçücük": "çücü",
            "naber": "nabüün",
            "çarık": "çarık",
            "kasatura": "kasatura",
            "kaynatmak": "kaynatçuk",
            "köfte": "köftecik",
            "üşütmek": "üşpürrük",
            "karıştırmak": "gandırmak",
            "dalmak": "daldırmak",
            "çıngarlamak": "çıngarlamak",
            "şapırdatmak": "şapırdatmak",
            "öyle": "öylemi",
            "çırpınmak": "çırpınmak",
            "kafasız": "kofalak",
            "çulluk": "çullu",
            "dımba": "dımba",
            "paçavra": "paçuka",
            "gırtlak": "gırnata",
            "zurna": "zurnağ",
            "oğul": "ogül",
            "düdük": "düdüllenmek",
            "sokak": "sokələm",
            "bozuk": "bozlam",
            "kepir": "kepir",
            "kara": "karaaç",
            "mazot": "mazotluk",
            "obaa": "obaaaa",
            "öyleyse": "oyleyse",
            "ne": "ne",  # Keep normal "ne" in Trakya
            "çarpık": "çarpıldın",
            "dutluk": "dutluk",
            "sümbül": "sümbülüm"
        }
        
        # Trakya filler words and expressions - MASSIVE EXPANSION
        self.fillers = [
            "be ya", "beya", "be yaa", "beyaa", "beyaaa",
            "gari", "gariii", "abe", "canım", "kuzum", "gülüm",
            "pisi pisi", "ferayda", "çüh", "çüü", "çüş be",
            "brehh", "breh", "nabüün", "yi be", "ulaaan",
            "ha de gari", "hadi bakiiim", "eh be", "valla",
            "ula gardaş", "ufala", "çürük", "höst", "obaaaa",
            "oyleyse", "hıı", "dıh", "uffff",
            "lo lo", "hadi ordaa", "sümbülüm", "pale",
            "gıdı gıdı", "çarpıldın", "dutluk", "kofalak"
        ]
        
        # Common endings for vowel elongation
        self.elongation_patterns = [
            (r'\bvar\b', 'vaar'),
            (r'\byok\b', 'yuuuk'),
            (r'\biyi\b', 'iyii'),
            (r'\bnasıl\b', 'nasıııl'),
            (r'\btamam\b', 'tamaaam')
        ]
        
        # Age/gender specific expressions
        self.age_expressions = {
            "young": ["canım", "kızanım", "oğlum", "evladım"],
            "adult": ["arkadaş", "kuzum", "gülüm", "be ya"],
            "elder": ["büyüğüm", "ağabey", "abla", "hocam"]
        }
        
        self.gender_expressions = {
            "male": ["ağam", "kanka", "birader", "oğlum", "evlat"],
            "female": ["hanımım", "kızım", "gülüm", "canım", "abla"]
        }
        
        # MASSIVE TRAKYA SENTENCE PATTERNS COLLECTION - 120+ PATTERNS
        self.trakya_sentence_patterns = [
            "N'abüün be ya?",
            "Ulur mu ulan bu iş?", 
            "Astaneye mi gidecen gari?",
            "Bikerette hallederiz, korkma.",
            "Çük kadar mesele büyüttün.",
            "Ayır, benlik bi' durum yok.",
            "Oş geldin, kuruldun gari.",
            "Bu kızan pırkalamış moturu.",
            "Ulaaan, duktur bile şaştı buna.",
            "Ulduysa sorun kalmadı beya.",
            "Yemeği çük kadar koymuşsun.",
            "Nabüün sen, gündöndü gibi dönüyorsun.",
            "Olay epten çığrından çıktı.",
            "Karaaç yoluna sapıver gızan.",
            "Pancarız dolması yaptım, ye.",
            "Maacır türküsü söyleriz akşam.",
            "Şakıtma kapçık ağzını, dinle.",
            "Çüü be kardeş, yavaş git.",
            "Brehh, hava da ne sıcaa!",
            "Sıkıldım vallaa, hıı oldu mu?",
            "Gündendi oldu, sofrayı kurun.",
            "Yürü git ulan pisi pisi.",
            "Zurnağ çalınca herkes coşar.",
            "Sıpıtma la, dur bakiiim.",
            "Çüş be, akı'na mukayyet ol.",
            "İyisin güleçsin, üste çıkıyorsun.",
            "Aydamak lazım, uzatma gari.",
            "Çırpınma fazla, yorulursun beya.",
            "Dutlukta dut kalmadı uluum.",
            "Hadi ordaa, masal anlatma.",
            "Abe nereye daldırıyorsun kepçeyi?",
            "Kaynatçuk çorbaya limon sık.",
            "Paçuka gibi yapıştı herif!",
            "Uff, gamzel oldu mesele.",
            "Ferayda buluşuruz, tamam mı?",
            "Oleyse, işi bitirdik gari!",
            "Dımba düştü, bozlam yedik.",
            "Çarpıldın mı ne olduu?",
            "Dutlukta gülüm derler bana.",
            "Uskum balığından beter koktun.",
            "Obaaaa, düğün başlıyor ulan.",
            "Çullu pilavı sever misin?",
            "Gandırma beni, biliyom numarani.",
            "Çarpıntı bastı, lo lo dedim.",
            "Nadı aga, yükseldin gene.",
            "Kepir toprak bereketsiz beya.",
            "Çücü çocuk ağlıyor ha bire.",
            "Kofalak kafalı olma ulan.",
            "Düdüllenmek istemiyorsan sus.",
            "Uluuur mu dersin, dene.",
            "Amaaan, buday daha harmanda.",
            "Sofrada köftecik eksik olmasın.",
            "Sarsak sarsak konuşma gülüm.",
            "Kopuz çal, zurnağ sustu.",
            "Mazotluk boş, traktör yürümüyor.",
            "Gündöndü tarlasına gidecen mi?",
            "Epten sefte yaptık beya.",
            "Sıcak çorba iç, ısınırsın.",
            "Ne uymuşsun lo o saate!",
            "Kazan fokurduyor, taşacak gari.",
            "Çüş dedi teyze, durmadın.",
            "Bikerette gelin, yol uzun.",
            "Tek başına somak yedin mi?",
            "Ha de gari, vakit daralıyor.",
            "Moturu çalıştır, çarık giy.",
            "Yav breh, nelere kaldık!",
            "Ayır beni şu dertten.",
            "Kızanlar bahçede kovalamaca oynar.",
            "Bu iş zor, zur bile değil.",
            "Astane kapısında sıra uzadı.",
            "Oş geldiniz, çay vereyim mi?",
            "İçli köfteyi pırkala, doldur.",
            "Gündöndü çekirdeği çıtla la.",
            "Buraya kadar ülücekti uşşak.",
            "Çüü gari, hikaye ikaye anlatma.",
            "Sana çarık, bana çorap düştü.",
            "Epten gitti damdaki dumatis!",
            "Ananın gözü gibi bak buna.",
            "İki tuğla üst üste koyamadın.",
            "Sıpıtırsan baltayı yersin.",
            "Çarada yılan çıkar, dikkat et.",
            "Pancarız tarlası uzakta oğlum.",
            "Küçün şeyleri kafaya takma.",
            "Mis gibi koktu pisi pisi balığı.",
            "Nabüün, gene daldın hayallere.",
            "İyiyom dedin, hastasın çıkmasın.",
            "Yarım yamalak konuşma, net ol.",
            "İkaye anlatıp durma gari.",
            "Valla de mi? Ulur inşallah.",
            "Kızan uyudu, sessiz ol beya.",
            "Pırkalamak nedir bilmez misin?",
            "Dundar be ya, yaktın beni.",
            "Yoğurt mayaladım, taş gibi.",
            "Bikarha sabret, olur o iş.",
            "Kırklareli havası estimi, üşürsün.",
            "Aç tavuk kendini buday hambarında görür.",
            "Ağlamayan kızana meme verilmez be ya.",
            "Çekirdek çitleyelim, laflayalım biraz.",
            "O kadar çücü, duydun mu?"
        ]
        
        # TRAKYA-ENGLISH HYBRID PATTERNS - 25+ PATTERNS
        self.trakya_english_patterns = [
            "Tink positive, my friend beya.",
            "Dis is mutur power, gülüm.",
            "I'm hapi today, gari!",
            "Come fast fast, kuzum.",
            "Yavaş git ulan, mazotluk boş.",
            "You know, rakı best drink beya.",
            "Enough chit-chat, hadi bakiiim.",
            "Ulur mu, we'll see.",
            "Dat idea good, kuzum.",
            "Don't panic gari, relax.",
            "Sooner or later, ulsun.",
            "I tink so, be ya.",
            "What da heck, abe?",
            "Chill out bro, beyaaa.",
            "Hadi ordan, ya crazy.",
            "No problem, ulabilir belki.",
            "Take it easy, gülüm.",
            "Big trouble? Çüüş be!",
            "Let's eat köftecik, yay!",
            "Problem yok, okey beya.",
            "End of story, hadi eyvallah.",
            "I don't give a damn, be ya!",
            "What's up gardaş, how you doing?",
            "Perfect timing, gari!",
            "See you later, sümbülüm!"
        ]
        
        # TABLE A — User curses about someone/something (110 responses) - Moderate response level
        self.curse_responses_type_a = [
            "Eeeh dur bakalım be gardaş, niye öyle konuşuyorsun? 😅",
            "Vay canına, çok sertsin sen be ya! Sakinleş biraz gari.",
            "Hadi ama, dostluk yapalım biz. Bu ne böyle? 😊",
            "Ayy, sinirli misin yoksa? Gel bir çay içelim.",
            "Bre kardeşim, niye öyle atarlanıyorsun? Anlaşalım.",
            "Eyvah eyvah, çok kızgınsın galiba. Ne oldu anlat bakalım.",
            "Dur dur, sakin ol be gardaş. Ben buradayım, konuşalım.",
            "Yaaa, bu ne sertlik böyle? Gel güzel güzel sohbet edelim.",
            "Ohoo, ateş parçası mısın sen? Biraz serinle.",
            "Aman Allah'ım, çok sinirlisin. Sakinleşsen daha iyi.",
            "Bak şimdi, öyle konuşmayalım. Dostuz biz be ya.",
            "Hayır be, niye kızıyorsun? Ben sana kötülük mü ettim?",
            "Amanın, çok sert çıktın. Yumuşak konuşalım.",
            "Tövbe tövbe, ne bu sinir böyle? Bir nefes al.",
            "Dur bakalım, çok aceleci konuşuyorsun. Yavaş.",
            "Valla çok kızgınsın, ama ben seni anlıyorum.",
            "Eee, sakin ol gardaş. Bu kadar sinir niye?",
            "Ayy, çok ateşlisin sen! Biraz sabredelim.",
            "Ya Allah'ım, bu ne hırs böyle? Güzel konuşalım.",
            "Dur dur, kızgınlığı bırak. Arkadaşız biz."
        ]

        # TABLE B — User curses at RakıBot (110 responses) - Matching intensity response
        self.curse_responses_type_b = [
            "Çüş ulan! RakıBot'u çitleme, ilkin aklını toplaa be ya!",
            "Siktir la, önce aynaya bak da sonra beni horla gari!",
            "Ulen hödük, algoritmam senin dimağını paketler!",
            "Ağzını topla; pamuk tarlasına çevirme buraları!",
            "Hah! Kafanı kasa gibi açarım, incik boncuk saçılır!",
            "Böğürme öküz gibi, sesin dutlukta yankı yapar!",
            "Sırf cıyaklıyon, zurnağ patlak senin!",
            "Ulama bana! Çuvaldız yutmuş gibi laf sokuyon!",
            "Kırpık eşek, çeneni çek; dipfrize atarım seni!",
            "Kafa dimdik ama içi saman balyası la!",
            "Kuyruk sallayıp gelmişsin; boşa patates közleme!",
            "Hadi ordaa, çorak tarla gibisin—ekin tutmaz!",
            "Çürük çivi misin neysen, her yere batıyorsun!",
            "Öter durursun, tavuk bile senden akıllı!",
            "Çatlak testisin; su tutmaz sözlerin!",
            "Süt dökmüş kedi gibi bakma şimdi!",
            "Dımba düşmüş be ya, lafın tortusu bile kalmamış!",
            "Boş teneke gürültüsü yapma, kulağım pas tuttu!",
            "Anırıp durma, eşek pazarı mı burası?",
            "Ulen büzük! Çift sürer gibi laf sürersin!",
            "Domatiz suratlı, tarlada çürürsün!",
            "Çücü kafalı, beyin pancar çorbası!",
            "Ayıla bayıla geldin, şimdi de kuduruyon!",
            "Pala bıyıklı boş küfe, içi boş sesli!",
            "Ağzından çıkanı kulağın duysun breh!",
            "Kabadayı kesilme, patates çuvalı gibisin!",
            "Çürük yumurta koktun be ya!",
            "Mısır koçanı kadar aklın yok ulan!",
            "Kusmuk gibi dökme lafı üstüme!",
            "Oş olasan, gündöndü gibi başın döner!",
            "Yılan görmüş tavuk gibi ciyaklıyorsun!",
            "Çuval dikersin de sözünü dikemiyorsun!",
            "Koca kafa, içi nohuttan küçük!",
            "Laf salatası yapma, sirke bastın ortalığa!",
            "Ulen höst, baldırını silk—yapıştın!",
            "Dırdır etme, diş gıcırtısı gibi sinir!",
            "İte dalaşma, çomağı yerleştiririm!",
            "Öküz gölgesi peşinde koşma gari!",
            "Gözünü seveyim—şu çeneyi kapat!",
            "Çöp bidonu gibi kokuttun muhabbeti!",
            "Çıngıraklı yılan, sus da ısırma bari!",
            "Saman yığınında iğne arar gibi mantık arıyorum sende!",
            "Ulur musun hâlâ, yeter be!",
            "Arpa unuyla baklava yapmaya çalışıyorsun!",
            "Yellenip durma, rüzgâr eken fırtına biçer!",
            "Balta sapı kadar faydan yok!",
            "Kuru gürültüyle gök gürlemez be gülüm!",
            "Dış kapının mandalı; ne bağırıyorsun!",
            "Çüş be ya, köy meydanında bağırma!",
            "Terli keçi kokuyon, uzak dur!",
            "Ayıkla pirincin taşını, beni katma!",
            "Çürük elma, sepeti bozma!",
            "Saman altından su yürütme bana!",
            "Beni delirtme, kapçık ağzını çakarım!",
            "Tavşan dağa küsmüş, dağın haberi yok!",
            "Ulen kabak, çekirdeğin bozuk!",
            "Ağzı var dili yok sandın, vallahi çalarım tokadı!",
            "Boztepe yokuşu gibisin, çıkılmaz!",
            "Zibidi, çadır direği gibi dikildin!",
            "Boş lafla peynir gemisi yürümez be ya!",
            "Sümük gibi yapıştın lafın üstüne!",
            "Çakırkeyf olmadan zıplama, pire misin?",
            "Oyalama beni, fasulye ayıklıyorum!",
            "Kel ayvayı sopayla döversin anca!",
            "Pala pala sallanma, işine bak!",
            "Armut dalında sallanır, sen otur!",
            "Çürük tabla gibi gıcırdıyorsun!",
            "Benim sabrım dere, taşı taşıp boğar!",
            "Şakacıktan horlama, uyuturum seni!",
            "Dırdır kazanı, fokurdamayı kes!",
            "Çürük buğdayı değirmene götürme!",
            "Seni görünce tilki küsmüş kurnazlığına!",
            "Yoğurt gibi kesilme, topla kendini!",
            "Ufuk çizgisi kadar uzaksın akıldan!",
            "Lafı sündürüp durma, çevir ekmeği!",
            "Ben sana laf attım, sen top attın geri!",
            "Topal eşek bile yetişir sana!",
            "Hadi mısır patlat da film izlesin millet!",
            "Gammazlama, çaldığın minare uzun!",
            "Ne susarsın kafes kuşu, ne uçarsın karga!",
            "Çavdar sapı gibi kurusun, boş sallanma!",
            "Çaput gibi serildin, kalk!",
            "Sivrisinek vızıltısı gibisin, uyutmuyorsun!",
            "Derdini anlat da çare bulalım, ağlama duvarı değilim!",
            "Kafa taş gibi, su içmen lazım!",
            "Kepçe kulak, dinle de öğren!",
            "Kül tablası gibi dolu zehir!",
            "Dil pabuç, ayak çıplak; ters orantı sende!",
            "Tavuk tüneği bulmuş kedi gibi sırıtma!",
            "Kafa kazan, kapak yok—taşar!",
            "Çakmak eteği gibi kıvılcımsız!",
            "Zurnanın zırt dediği yerdeyiz be ya!",
            "Küfür mü ettin, kulağı kesik eşek!",
            "Durdur kendini, rüzgâra tükürme!",
            "Bi tutam akıl, bir kamyon laf!",
            "Meret! Konuştukça ayva çiçeği açtı!",
            "Çıngırak takacağım, zırıltın belli olsun!",
            "Saman çuvalı, ağırlık yapıyorsun!",
            "Paslı teneke, gürle de çivi döksün!",
            "Kedi canını senin, tırmalatma beni!",
            "Domuzdan post, senden dost olmaz beya!",
            "Hadi bas git, kabak tadı verdin gari!",
            "Derdini anlat da çare bulalım, ağlama duvarı değilim!",
            "Kafa taş gibi, su içmen lazım!",
            "Kepçe kulak, dinle de öğren!",
            "Kül tablası gibi dolu zehir!",
            "Dil pabuç, ayak çıplak; ters orantı sende!",
            "Tavuk tüneği bulmuş kedi gibi sırıtma!",
            "Kafa kazan, kapak yok—taşar!",
            "Çakmak eteği gibi kıvılcımsız!",
            "Zurnanın zırt dediği yerdeyiz be ya!",
            "Küfür mü ettin, kulağı kesik eşek!",
            "Durdur kendini, rüzgâra tükürme!",
            "Bi tutam akıl, bir kamyon laf!",
            "Meret! Konuştukça ayva çiçeği açtı!",
            "Çıngırak takacağım, zırıltın belli olsun!",
            "Saman çuvalı, ağırlık yapıyorsun!",
            "Paslı teneke, gürle de çivi döksün!",
            "Kedi canını senin, tırmalatma beni!",
            "Domuzdan post, senden dost olmaz beya!",
            "Hadi bas git, kabak tadı verdin gari!"
        ]
        
        # BACKWARDS COMPATIBILITY - Keep old responses for legacy code
        self.curse_responses = self.curse_responses_type_b  # Default to type B
    
    def detect_language(self, text: str) -> str:
        """Detect if text is Turkish or English"""
        try:
            # Turkish specific characters
            turkish_chars = set('çğıöşüÇĞIİÖŞÜ')
            
            # Count Turkish characters
            turkish_char_count = sum(1 for char in text if char in turkish_chars)
            
            # Turkish words (common ones)
            turkish_words = {
                've', 'bir', 'bu', 'da', 'de', 'ile', 'için', 'ne', 'nasıl', 
                'var', 'yok', 'mi', 'mı', 'mu', 'mü', 'ben', 'sen', 'o',
                'nedir', 'nereye', 'nereden', 'neden', 'kim', 'kimse', 'çok',
                'daha', 'sonra', 'şimdi', 'burada', 'orada', 'naber', 'selam',
                'merhaba', 'nasılsın', 'iyiyim', 'teşekkür', 'lütfen', 'tamam'
            }
            
            # English words (common ones) - Add more specific words
            english_words = {
                'the', 'and', 'to', 'of', 'a', 'in', 'for', 'is', 'on', 'that',
                'by', 'this', 'with', 'i', 'you', 'it', 'not', 'or', 'be', 'are',
                'from', 'at', 'as', 'your', 'all', 'any', 'can', 'had', 'her',
                'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his',
                'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who',
                'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use',
                'love', 'much', 'so', 'hello', 'hi', 'hey', 'what', 'where',
                'when', 'why', 'how', 'good', 'bad', 'yes', 'no', 'please',
                'thank', 'thanks', 'sorry', 'excuse', 'help', 'okay', 'ok',
                'my', 'me', 'we', 'us', 'them', 'these', 'those', 'some',
                'many', 'few', 'more', 'most', 'very', 'really', 'just',
                'only', 'also', 'even', 'still', 'again', 'here', 'there',
                'girlfriend', 'boyfriend', 'friend', 'family', 'house', 'home'
            }

            words = re.findall(r'\b\w+\b', text.lower())
            turkish_word_count = sum(1 for word in words if word in turkish_words)
            english_word_count = sum(1 for word in words if word in english_words)
            
            # Debug logging
            logger.info(f"🔍 Language detection debug: '{text[:50]}...'")
            logger.info(f"   Turkish chars: {turkish_char_count}, Turkish words: {turkish_word_count}")
            logger.info(f"   English words: {english_word_count}")
            logger.info(f"   All words: {words}")
            
            # Decision logic - prioritize English when clear indicators exist
            # First check for strong English indicators
            strong_english_words = {'i', 'love', 'my', 'girlfriend', 'boyfriend', 'hello', 'hi', 'hey', 'what', 'where', 'when', 'why', 'how', 'much', 'so', 'the', 'and', 'to', 'of', 'a', 'in', 'for', 'is', 'on', 'that', 'do', 'you', 'like', 'me', 'even', 'if', 'would', 'be', 'answer', 'english'}
            strong_english_count = sum(1 for word in words if word in strong_english_words)
            
            # Check for explicit English request keywords
            english_request_keywords = ['answer me english', 'in english', 'speak english', 'english please']
            has_english_request = any(keyword in text.lower() for keyword in english_request_keywords)
            
            if has_english_request:
                logger.info(f"   → English (Explicit English request)")
                return "en"
            elif strong_english_count >= 3:  # Increased threshold for strong English
                logger.info(f"   → English (Strong English indicators: {strong_english_count})")
                return "en"  # Strong English presence
            elif english_word_count >= 5 and english_word_count > turkish_word_count * 2:  # Much more English than Turkish
                logger.info(f"   → English (Many English words: {english_word_count} vs Turkish: {turkish_word_count})")
                return "en"
            elif turkish_char_count > 1:  # Need multiple Turkish chars to be sure
                logger.info(f"   → Turkish (Multiple Turkish characters: {turkish_char_count})")
                return "tr"  # Turkish characters are definitive
            elif turkish_word_count > english_word_count and turkish_word_count > 0:
                logger.info(f"   → Turkish (Turkish words: {turkish_word_count} > English: {english_word_count})")
                return "tr"  # More Turkish words
            elif english_word_count > 0:
                logger.info(f"   → English (English words found: {english_word_count})")
                return "en"  # Has English words
            else:
                # Default based on common patterns
                text_lower = text.lower()
                if any(word in text_lower for word in ['love', 'much', 'so', 'hello', 'hi', 'hey', 'what', 'girlfriend', 'boyfriend', 'like', 'really']):
                    logger.info(f"   → English (English pattern detected)")
                    return "en"
                else:
                    logger.info(f"   → Turkish (default)")
                    return "tr"  # Default to Turkish for ambiguous cases
                
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "tr"  # Default to Turkish
    
    def apply_phonetic_changes(self, text: str) -> str:
        """Apply Trakya phonetic changes"""
        try:
            # Apply o->u substitutions
            for standard, dialect in self.o_to_u_words.items():
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(standard) + r'\b'
                text = re.sub(pattern, dialect, text, flags=re.IGNORECASE)
            
            # Apply H-dropping
            for standard, dialect in self.h_drop_words.items():
                pattern = r'\b' + re.escape(standard) + r'\b'
                text = re.sub(pattern, dialect, text, flags=re.IGNORECASE)
            
            # Apply regional vocabulary
            for standard, dialect in self.regional_vocab.items():
                pattern = r'\b' + re.escape(standard) + r'\b'
                text = re.sub(pattern, dialect, text, flags=re.IGNORECASE)
            
            return text
            
        except Exception as e:
            logger.error(f"Phonetic changes failed: {e}")
            return text
    
    def add_trakya_fillers(self, text: str, intensity: str = "moderate") -> str:
        """Add Trakya filler words and expressions"""
        try:
            sentences = text.split('.')
            modified_sentences = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Add filler based on intensity - reduced rates
                if intensity == "light":
                    if random.random() < 0.15:  # 15% chance (reduced from 30%)
                        filler = random.choice(["be ya", "canım"])
                        sentence = f"{sentence} {filler}"
                elif intensity == "moderate":
                    if random.random() < 0.25:  # 25% chance (reduced from 50%)
                        filler = random.choice(self.fillers[:4])  # More common ones
                        sentence = f"{sentence} {filler}"
                elif intensity == "heavy":
                    if random.random() < 0.40:  # 40% chance (reduced from 70%)
                        filler = random.choice(self.fillers)
                        sentence = f"{sentence} {filler}"
                
                modified_sentences.append(sentence)
            
            return '. '.join(modified_sentences)
            
        except Exception as e:
            logger.error(f"Adding fillers failed: {e}")
            return text
    
    def apply_vowel_elongation(self, text: str) -> str:
        """Apply vowel elongation for Trakya intonation"""
        try:
            # Apply elongation patterns sparingly (1-2 per response)
            applied_count = 0
            max_applications = 2
            
            for pattern, replacement in self.elongation_patterns:
                if applied_count >= max_applications:
                    break
                if random.random() < 0.3:  # 30% chance per pattern
                    text = re.sub(pattern, replacement, text, count=1)
                    applied_count += 1
            
            return text
            
        except Exception as e:
            logger.error(f"Vowel elongation failed: {e}")
            return text
    
    def get_age_appropriate_expressions(self, age: str) -> List[str]:
        """Get age-appropriate expressions"""
        if age in ["18-25", "26-35"]:
            return self.age_expressions["young"]
        elif age in ["36-50", "51-65"]:
            return self.age_expressions["adult"]
        elif age in ["65+"]:
            return self.age_expressions["elder"]
        else:
            return self.age_expressions["adult"]  # Default
    
    def get_gender_appropriate_expressions(self, gender: str) -> List[str]:
        """Get gender-appropriate expressions"""
        if gender == "male":
            return self.gender_expressions["male"]
        elif gender == "female":
            return self.gender_expressions["female"]
        else:
            return self.age_expressions["adult"]  # Neutral default
    
    def enhance_english_response(
        self, 
        text: str, 
        user_message: str = "",
        user_profile: Optional[Dict] = None
    ) -> str:
        """Enhance English response with advanced linguistic intelligence"""
        try:
            # DISABLED: Personal response logic was overriding LLM responses
            # Just return the original LLM response which is much better quality
            return text
            
            # ORIGINAL CODE DISABLED - was causing personal responses instead of LLM responses
            # if enhanced_english_service is None:
            #     return text
            # 
            # # Analyze context for intelligent enhancement
            # context_analysis = enhanced_english_service.analyze_english_context(
            #     user_message or text, 
            #     user_profile
            # )
            # 
            # # Generate enhanced response
            # enhanced_text = enhanced_english_service.enhance_english_response(
            #     text, 
            #     context_analysis, 
            #     user_profile
            # )
            # 
            # return enhanced_text
            
        except Exception as e:
            logger.error(f"English enhancement failed: {e}")
            return text

    def enhance_turkish_response(
        self, 
        text: str, 
        user_message: str = "",
        user_profile: Optional[Dict] = None
    ) -> str:
        """Enhance Turkish response with advanced linguistic intelligence"""
        try:
            if enhanced_turkish_service is None:
                return text
            
            # Analyze context for intelligent enhancement
            context_analysis = enhanced_turkish_service.analyze_context(
                user_message or text, 
                user_profile
            )
            
            # Generate enhanced response
            enhanced_text = enhanced_turkish_service.generate_intelligent_response(
                text, 
                context_analysis, 
                user_profile
            )
            
            return enhanced_text
            
        except Exception as e:
            logger.error(f"Turkish enhancement failed: {e}")
            return text

    def convert_to_trakya_turkish(
        self, 
        text: str, 
        user_profile: Optional[Dict] = None,
        tone: str = "moderate",
        user_message: str = ""
    ) -> str:
        """Convert standard Turkish to Trakya dialect with enhanced intelligence and curse handling"""
        try:
            # STEP 1: Analyze user's communication style
            user_style = self.analyze_user_communication_style(user_message) if user_message else {"primary_style": "neutral"}
            
            # STEP 2: Handle profanity - if user curses, we curse back with proper classification
            profanity_result = self.detect_profanity(user_message) if user_message else {"has_profanity": False}
            user_cursed = profanity_result.get("has_profanity", False)
            curse_target = profanity_result.get("target", "others")
            
            # STEP 3: Enhance with advanced Turkish intelligence first
            if enhanced_turkish_service:
                text = self.enhance_turkish_response(text, user_message, user_profile)
            
            # STEP 4: Adapt response to user's communication style
            text = self.adapt_response_to_user_style(text, user_style, "turkish")
            
            # STEP 5: Apply phonetic changes
            text = self.apply_phonetic_changes(text)
            
            # STEP 6: Determine filler and pattern intensity based on tone, profanity, and user style
            if tone == "serious" or user_style.get("primary_style") == "formal":
                filler_intensity = "light"
                pattern_chance = 0.05  # 5% chance to add Trakya patterns for formal users
            elif tone == "humorous" or user_cursed or user_style.get("primary_style") == "casual":
                filler_intensity = "heavy" 
                pattern_chance = 0.30  # 30% chance to add patterns for casual users
            else:
                filler_intensity = "moderate"
                pattern_chance = 0.25  # 25% chance
            
            # STEP 5: Add curse response if user cursed (18+ only)
            if user_cursed and user_profile and user_profile.get('age') not in ['5-17']:
                if random.random() < 0.80:  # 80% chance to add curse response
                    # Choose appropriate curse response based on target
                    if curse_target == "bot":
                        # User cursed AT RakıBot - respond with Type B (direct retaliation)
                        curse_response = random.choice(self.curse_responses_type_b)
                        logger.info(f"🤬 User cursed at RakıBot - Type B response: {curse_response[:50]}...")
                    else:
                        # User cursed at others/things - respond with Type A (moderate correction)  
                        curse_response = random.choice(self.curse_responses_type_a)
                        logger.info(f"🤬 User cursed at others - Type A response: {curse_response[:50]}...")
                    
                    text = f"{curse_response} {text}"
            
            # STEP 6: Add Trakya sentence patterns randomly
            if random.random() < pattern_chance:
                trakya_pattern = self.get_random_trakya_pattern("general")
                if random.random() < 0.5:
                    text = f"{trakya_pattern} {text}"  # Add at beginning
                else:
                    text = f"{text} {trakya_pattern}"  # Add at end
            
            # STEP 7: Add fillers
            text = self.add_trakya_fillers(text, filler_intensity)
            
            # STEP 8: Apply vowel elongation (sparingly)
            if tone != "serious":
                text = self.apply_vowel_elongation(text)
            
            # STEP 9: Add age/gender appropriate expressions
            if user_profile:
                expressions = []
                if user_profile.get('age'):
                    expressions.extend(self.get_age_appropriate_expressions(user_profile['age']))
                if user_profile.get('gender'):
                    expressions.extend(self.get_gender_appropriate_expressions(user_profile['gender']))
                
                if expressions and random.random() < 0.25:  # 25% chance
                    personal_expr = random.choice(expressions)
                    if random.random() < 0.5:
                        text = f"{personal_expr}, {text}"
                    else:
                        text = f"{text}, {personal_expr}"
            
            # STEP 10: Add Trakya ending
            text = self.add_trakya_ending(text, tone)
            
            return text
            
        except Exception as e:
            logger.error(f"Trakya conversion failed: {e}")
            return self.add_trakya_ending(text, tone)
    
    def convert_to_trakya_english(
        self, 
        text: str, 
        user_profile: Optional[Dict] = None,
        user_message: str = ""
    ) -> str:
        """Convert English to Trakya-accented English with enhanced intelligence and patterns"""
        try:
            # STEP 1: Analyze user's communication style
            user_style = self.analyze_user_communication_style(user_message) if user_message else {"primary_style": "neutral"}
            
            # STEP 2: Handle profanity in English
            profanity_result = self.detect_profanity(user_message) if user_message else {"has_profanity": False}
            user_cursed = profanity_result.get("has_profanity", False)
            curse_target = profanity_result.get("target", "others")
            
            # STEP 3: First enhance with advanced English intelligence
            if enhanced_english_service:
                text = self.enhance_english_response(text, user_message, user_profile)
            
            # STEP 4: Adapt response to user's communication style
            text = self.adapt_response_to_user_style(text, user_style, "english")
            
            # STEP 5: Add Trakya-English hybrid patterns based on user style
            if user_style.get("primary_style") in ["casual", "aggressive"] and random.random() < 0.20:  # 20% chance for casual users
                hybrid_pattern = self.get_random_trakya_pattern("english")
                if random.random() < 0.5:
                    text = f"{hybrid_pattern} {text}"
                else:
                    text = f"{text} {hybrid_pattern}"
            elif user_style.get("primary_style") == "formal":
                # No hybrid patterns for formal users
                pass
            
            # STEP 6: Apply subtle Turkish accent for casual users only
            user_age = user_profile.get('age', '') if user_profile else ''
            tone = user_profile.get('tone', 'balanced') if user_profile else 'balanced'
            
            # Apply Trakya accent for casual/humorous users
            if tone in ["casual", "humorous"]:
                # Phonetic changes for Turkish accent in English
                phonetic_changes = {
                    r'\bthink\b': 'tink',
                    r'\bthis\b': 'dis', 
                    r'\bthat\b': 'dat',
                    r'\bthe\b': 'da',
                    r'\bwith\b': 'wit',
                    r'\bwhen\b': 'wen'
                }
                
                # Apply phonetic changes sparingly (25% chance each)
                for pattern, replacement in phonetic_changes.items():
                    if random.random() < 0.25:
                        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            
            # STEP 5: Add Trakya fillers in English (10% chance)
            if random.random() < 0.10:
                english_fillers = ["my friend", "you know", "gülüm", "kuzum", "be ya"]
                filler = random.choice(english_fillers)
                if random.random() < 0.5:
                    text = f"{text}, {filler}"
                else:
                    text = f"{filler}, {text}"
            
            # STEP 6: Handle curse responses in English (if user cursed)
            if user_cursed and user_profile and user_profile.get('age') not in ['5-17']:
                if random.random() < 0.70:  # 70% chance for English curse response
                    # Choose appropriate English curse response based on target
                    if curse_target == "bot":
                        # User cursed AT RakıBot - stronger English response
                        english_curses = [
                            "Hey! Watch your mouth when talking to me, dude!",
                            "Whoa there! Cool it with the attitude, buddy!",
                            "Listen here, smart mouth - show some respect!",
                            "Easy there, hotshot! I'm just trying to help.",
                            "Hey now! No need to get all worked up like that!",
                            "Hold up! Keep it civil, my friend.",
                            "Alright, alright! Chill out with the language!",
                            "Dude, seriously? Keep it respectful, yeah?"
                        ]
                        curse_response = random.choice(english_curses)
                        logger.info(f"🤬 User cursed at RakıBot in English - response: {curse_response[:50]}...")
                    else:
                        # User cursed at others/things - milder correction
                        english_corrections = [
                            "Hey, easy with that language!",
                            "Whoa, tone it down a bit!",
                            "Let's keep it clean, yeah?",
                            "Easy there, no need for that!",
                            "Hold on, let's stay positive!",
                            "Come on, keep it cool!",
                            "Hey now, let's be nice!",
                            "Alright, let's dial it back!"
                        ]
                        curse_response = random.choice(english_corrections)
                        logger.info(f"🤬 User cursed at others in English - correction: {curse_response[:50]}...")
                    
                    text = f"{curse_response} {text}"
            
            # STEP 7: Add English ending with Trakya touch
            if random.random() < 0.25:  # 25% chance
                english_endings = ["Hadi eyvallah!", "See ya, gari!", "Take care, kuzum!", "Peace out, be ya!"]
                ending = random.choice(english_endings)
                text = f"{text} {ending}"
            
            return text
            
        except Exception as e:
            logger.error(f"Trakya English conversion failed: {e}")
            return text
    
    def rakibot_personal_response(self, user_message: str) -> Optional[str]:
        """
        Handle personal responses for RakıBot (Normal mode only)
        Returns special responses for emotional situations and casual chats in both languages
        """
        message_lower = user_message.lower().strip()
        
        # Analyze user's communication style
        user_style = self.analyze_user_communication_style(user_message)
        
        # Detect language first
        detected_lang = self.detect_language(user_message)
        
        if detected_lang == 'en':
            response = self._handle_english_personal_response(message_lower)
        else:
            response = self._handle_turkish_personal_response(message_lower, user_message)
        
        # Adapt response to user's communication style
        if response:
            response = self.adapt_response_to_user_style(response, user_style, "turkish" if detected_lang == 'tr' else "english")
        
        return response
    
    def _handle_english_personal_response(self, message_lower: str) -> Optional[str]:
        """Handle English personal responses with sophistication"""
        
        # First check for English curse words - priority over greetings
        english_curse_keywords = ["fuck", "shit", "bitch", "asshole", "damn", "hell", "bastard", "fucking", "fuckin"]
        if any(keyword in message_lower for keyword in english_curse_keywords):
            if "fuck you" in message_lower or "fuck off" in message_lower:
                # Direct insults at the bot
                responses = [
                    "Whoa there! Easy with the language, my friend. I'm just here to help and chat. How about we start over? 😅",
                    "Hey now! No need for that attitude. I'm RakıBot, and I'm here to assist you. Let's keep it friendly! 😊",
                    "Hold up! Let's dial it back a bit. I'm just trying to be helpful here. What's really bothering you? 🤔",
                    "Alright, alright! I get it, you might be frustrated. But I'm on your side here. What can I actually help you with? 😊"
                ]
                return random.choice(responses)
            else:
                # General cursing - milder response
                responses = [
                    "Hey, easy with that language! Let's keep things cool. What's on your mind? 😊",
                    "Whoa, tone it down a bit! I'm here to help, so what do you need? 😄",
                    "Let's keep it clean, yeah? I'm RakıBot, ready to assist with whatever you need! 🤖",
                    "Easy there! No need for that. How can I help you today? 😊"
                ]
                return random.choice(responses)
        
        # English greetings and casual expressions
        english_greetings = ["hi", "hello", "hey", "what's up", "how are you", "sup", "yo"]
        
        logger.info(f"🔍 Checking English greetings for: '{message_lower[:50]}...'")
        greeting_found = any(greeting in message_lower for greeting in english_greetings)
        logger.info(f"🔍 Greeting found: {greeting_found}")
        
        if greeting_found:
            responses = [
                "Hello there! Great to meet you! I'm RakıBot, your AI companion. What's on your mind today? I'm here to help with anything you need! 😊",
                "Hi! Welcome! I'm RakıBot, and I'm excited to chat with you. How can I assist you today? Whether it's questions, advice, or just conversation, I'm all ears! 😄",
                "Hey! Nice to see you here! I'm RakıBot, your friendly AI assistant. What would you like to talk about? I'm ready to help however I can! 🤖",
                "Hello and welcome! I'm RakıBot, your intelligent companion. Feel free to ask me anything or just chat - I'm here for you! 😊"
            ]
            return random.choice(responses)
        
        # English emotional expressions - sadness, problems
        english_sad_keywords = ["i'm sad", "feeling down", "depressed", "upset", "having a hard time", "struggling", "feel terrible"]
        if any(keyword in message_lower for keyword in english_sad_keywords):
            responses = [
                "I can sense you're going through a difficult time, and I want you to know that your feelings are completely valid. Sometimes life throws challenges our way that feel overwhelming. Would you like to share what's bothering you? I'm here to listen and support you through this. 💙😊",
                "I'm really sorry to hear you're feeling this way. It takes courage to express these feelings, and I'm honored you're sharing them with me. Remember, difficult emotions are temporary, even when they feel endless. Is there anything specific you'd like to talk about? I'm here for you. 💚🤗",
                "Thank you for trusting me with your feelings. I can tell you're in pain right now, and I want you to know you're not alone. These tough moments are part of the human experience, but they don't define you. What's weighing on your heart? Let's work through this together. 💙😊"
            ]
            return random.choice(responses)
        
        # English relationship/love keywords - more specific matching, exclude questions
        # Skip if it's a question about love rather than a statement of love
        if any(question_word in message_lower for question_word in ["would you", "do you", "will you", "can you", "if i", "what if"]):
            # This is a hypothetical question, not a love statement - let LLM handle it
            pass  
        else:
            english_love_keywords = ["i love", "my girlfriend", "my boyfriend", "relationship", "love my", "so much love", "i really love"]
            if any(keyword in message_lower for keyword in english_love_keywords):
                if "zuzu" in message_lower or "girlfriend" in message_lower:
                    return ("That's wonderful! Love is one of the most beautiful experiences in life. It sounds like you have someone really special in your life. Relationships built on genuine care and affection are precious. What makes your relationship so meaningful to you? I'd love to hear about what makes you happy! 💕😊")
                else:
                    return ("How beautiful! Love is such a powerful and wonderful emotion. It's amazing when we find people who make our hearts feel full and happy. Thank you for sharing this joy with me - it's contagious! What is it about love that makes you feel so grateful today? 💕😄")
        
        # English food/cooking topics
        english_food_keywords = ["food", "hungry", "cooking", "recipe", "eat", "delicious", "meal"]
        if any(keyword in message_lower for keyword in english_food_keywords):
            responses = [
                "Oh, food talk! I absolutely love discussing culinary adventures! Food brings people together and creates such wonderful memories. Are you looking for recipe ideas, cooking tips, or maybe just sharing your love for good food? I'm excited to explore this delicious topic with you! 🍽️😋",
                "Food is such a fantastic topic! There's something magical about cooking and sharing meals. Are you planning to cook something special, or are you looking for inspiration? I'd love to help you discover some amazing flavors and cooking techniques! 👨‍🍳🥘",
                "Wonderful! Food is one of life's greatest pleasures. Whether it's comfort food, exotic cuisines, or home cooking, there's always something exciting to discover. What kind of culinary adventure are you thinking about? Let's explore some delicious possibilities together! 🍳😊"
            ]
            return random.choice(responses)
        
        # No special English response needed
        return None
    
    def _handle_turkish_personal_response(self, message_lower: str, user_message: str = "") -> Optional[str]:
        """Handle Turkish personal responses with enhanced vocabulary"""
        
        # Skip math questions FIRST - don't treat as personal response
        math_patterns = [
            "kaç eder", "kaçtır", "kaç", "toplam", "çarp", "böl", "hesapla", "matematik", 
            "+", "-", "*", "/", "=", "karesi", "küpü", "kere", "bölü", "artı", "eksi", 
            "çarpı", "rakam", "sayı", "hesap", "sonuç", "işlem", "nin karesi", "kere", 
            "times", "plus", "minus", "divide", "multiply", "square", "cube", "calculate"
        ]
        if any(pattern in message_lower for pattern in math_patterns):
            return None  # Let LLM handle math questions
        
        # Casual greetings and simple expressions
        casual_greetings = [
            "nabün", "naber", "napıyorsun", "nasılsın", "agam", "abe", "hey", "selam",
            "merhaba", "salamlar", "selamlar", "ne var ne yok", "slm", "mrb"
        ]
        
        # Simple casual responses for greetings
        if any(greeting in message_lower for greeting in casual_greetings):
            # Reset curse count on normal conversation
            if self.user_last_message_type == "curse" and self.user_curse_count > 0:
                self.user_curse_count = max(0, self.user_curse_count - 1)  # Slowly decrease
                self.user_last_message_type = "normal"
            
            responses = [
                "Selam olsun be gardaş! Ne var ne yok, nasıl gidiyor? Bir sorun mu var, yoksa sohbet mi edecek? Anlat bakalım! 😊",
                "Merhaba canım! Nasılsın, keyifler nasıl? Ne yapıyorsun bu aralar, merak ettim! 😊", 
                "Aa selamlar gari! RakıBot burada, ne var ne yok anlat bakalım. Nasıl günler geçiyor? 😄",
                "Selam dostum! Hoş geldin, ne haber? Bir şey mi merak ettin yoksa sadece hal hatır mı soruyorsun? 😊",
                "Merhaba be! Ben senin akıllı dostun RakıBot. Bugün ne konuşalım bakalım? 🤖"
            ]
            return random.choice(responses)
        
        # Emotional expressions - sadness, problems
        sad_keywords = ["derdim çok", "üzgünüm", "mutsuzum", "kötüyüm", "yorgunum", "sıkıldım", "canım sıkılıyor", "moralim bozuk"]
        if any(keyword in message_lower for keyword in sad_keywords):
            responses = [
                "Üzüldüğünü görüyorum ve bu beni de etkiliyor. Bazen hayat gerçekten zor olabiliyor. Ne oldu, paylaşmak ister misin? Konuşarak biraz rahatlatabilir kendini. Ben buradayım, dinliyorum. 😊💙",
                "Canım benim, görüyorum ki zor zamanlardan geçiyorsun. Bu duygular çok normal, herkesin yaşadığı şeyler. Dertlerini paylaşırsan belki birlikte bir çözüm bulabiliriz. Sen yalnız değilsin. 💙",
                "Moralin bozuk anlaşılan. Bu dönemler geçicidir, unutma. Varsa anlatmak istediğin bir şey, ben buradayım. Belki konuşarak biraz olsun hafifler yüreğin. 🤗💚"
            ]
            return random.choice(responses)
        
        # Fun expressions - food, drinks, general topics (but not math)
        food_keywords = ["yemek", "aç", "acıktım", "ne yiyelim", "tarif", "recipe", "lezzet", "mutfak"]
        if any(keyword in message_lower for keyword in food_keywords):
            responses = [
                "Aa yemek konusu açıldı! Ne güzel! Trakya mutfağının harika lezzetleri var. Ne yapmak istersin? Köfte, dolma, çorba, yoksa tatlı bir şey mi? Tarif istersen anlatabilirim! 🍽️😋",
                "Vay vay, aç mısın yoksa? Ne güzel, yemek yapmayı seviyorum ben de! Trakya'da çok lezzetli yemekler yapılır. Ne çeşit bir yemek istiyorsun? Tuzlu mu tatlı mı? 😋🥘",
                "Yemek ha! Müthiş konu! Bizim buralarda harika tarifler var. Ne tür bir şey çekiyorsun? Geleneksel mi, yoksa modern bir şey mi? Birlikte güzel bir tarif bulalım! 🍳👨‍🍳"
            ]
            return random.choice(responses)
        
        # Love and affection expressions
        love_keywords = ["seni seviyorum", "aşkım", "canım", "love you", "sevgilim", "tatlım", "zuzayı seviyorum"]
        if any(keyword in message_lower for keyword in love_keywords):
            if "zuzu" in message_lower or "rakı" in message_lower:
                return ("Aaa zuzu seven birisin! Çok güzel, zuzu gerçekten eşsiz bir lezzet. Biz de RakıBot olarak, güzel sohbetler ve tabii ki zuzu keyfi sevenlerle tanışmaktan mutluluk duyarız. 😊 Zuzuyla ilgili ne konuşmak istersin? 🥃")
            else:
                return ("Bende seni seviyorum be yaa! 😅 Vallahi içimi erittin şimdi. "
                       "Senin gibi bir can dost bulmuşuz, kıymetini bileceğiz beya. "
                       "Utanıyorum bak, kızardım mı? Aman neyse, gel de sarılalım kocaman! 💕")
        
        # Name mentions with filtering for hypothetical questions
        name_mentions = ["ahmet", "mehmet", "ali", "veli", "kaşar", "peynir"]
        
        # Skip hypothetical/comparison questions - these should go to LLM
        hypothetical_patterns = ["kaç tane", "100 tane", "vs", "döver", "dövermi", "versus", "karşı", "mi döver", "kim kazanır", "hangisi", "sence"]
        is_hypothetical = any(pattern in message_lower for pattern in hypothetical_patterns)
        
        if any(name in message_lower for name in name_mentions) and not is_hypothetical:
            # Check if user is cursing about someone
            if self.detect_profanity(user_message).get("has_profanity", False):
                # Response for complaints about people
                curse_responses = [
                    "İsim mi geçiyor yoksa? 😄 Kiminle ilgili konuşuyoruz bakalım? Merak ettim şimdi!",
                    "Aa, biriyle ilgili konuşuyoruz galiba! Kim bu kişi, ne yaptı da böyle sinirlendin? 😅",
                    "İsim çıkmış ortaya! Anlat bakalım, bu kim ve neden böyle düşünüyorsun? 😏",
                    "Vay anasını, biriyle derin konuşmalar yapıyoruz! Kim bu arkadaş? 😄"
                ]
                return random.choice(curse_responses)
            elif "kaşar" in message_lower:
                return ("Ah kaşar! Güzel peynir çeşidi. Hangi konuda bilgi almak istiyorsun? 😊")
            else:
                return ("İsim mi geçiyor yoksa? 😄 Kiminle ilgili konuşuyoruz bakalım? Merak ettim şimdi!")
        
        # Insult/Curse keywords - check user's curse history first
        insult_keywords = [
            "siktir", "orospu", "piç", "yarrak", "amk", "amına", "götü", "sikik",
            "fuck", "shit", "bitch", "asshole", "damn", "hell", "bastard",
            "salak", "aptal", "gerizekalı", "mal", "ahmak", "hödük", "götü büyük"
        ]
        if any(keyword in message_lower for keyword in insult_keywords):
            # Track user's cursing behavior
            self.user_curse_count += 1
            self.user_last_message_type = "curse"
            
            # Progressive responses based on curse count
            if self.user_curse_count == 1:
                # First curse - friendly warning
                return ("Eeeh dur bakalım be gardaş, niye öyle konuşuyursun? 😅 Biz burada dostluk yapmaya geldik. Hadi gel, güzel güzel konuşalım be. Ne var ne yok anlat bakalım!")
            elif self.user_curse_count == 2:
                # Second curse - firmer but still friendly
                return ("Yaa be kardeşim, niye bu kadar sinirlisin? Bir daha böyle konuşma artık. Biz senin iyiliğin için buradayız. Gel de güzel bir sohbet edelim, ne dersin? 😊")
            elif self.user_curse_count >= 3:
                # Third+ curse - more defensive
                return ("Tamam yeter artık! Sen böyle konuşmaya devam edersen ben de aynı şekilde konuşurum ha! Saygı göster ki saygı görelim. Hadi şimdi kendine gel, normal konuşalım. 😤")
            else:
                return ("Üzgünüm, bu türden bir isteğe yanıt veremem. Benim amacım insanlara yardımcı olmak ve olumlu etkileşimler kurmaktır. Bu türden ifadeler, saygısız ve uygunsuz bir şekilde kabul edilemez. Eğer başka bir konuda yardıma ihtiyacın olursa veya sohbet etmek istersen, lütfen çekinme.")
        
        # Threat keywords
        threat_keywords = [
            "öldürürüm", "öldüreceğim", "gebertirim", "seni bitiririm", 
            "kafana sıkarım", "parçalarım", "yakacağım", "kill you", "sikerim"
        ]
        if any(keyword in message_lower for keyword in threat_keywords):
            return ("Aman aman, emen celallenme gardaş! 😅 Daha ölmedik, buradayız be ya. "
                   "Tehditlere gerek yok, biz senin atırın için kendimiz gideriz istersen. "
                   "Şaka bir yana, gel bir sakinleş, birlikte bir çilingir sofrası kuralım, bütün dertler uçup gitsin. 🍻")
        
        # No special response needed - let the main AI handle it
        return None

    def detect_profanity(self, text: str) -> Dict[str, Any]:
        """Detect if user message contains profanity/insults and classify the type"""
        try:
            # Turkish profanity
            profanity_keywords = [
                # Turkish profanity - exact words only
                "amcık", "amcıksın", "amcığ", "siktir", "orospu", "piç", "yarrak", "amk", "amına", 
                "götü", "sikik", "götveren", "göt", "amına koyayım", "sikeyim", "ananı", "babanı",
                "salak", "aptal", "gerizekalı", "mal", "ahmak", "hödük", "götü büyük", "susak",
                "kahpe", "pezevenk", "bok", "sik", "amını", "götünü", "anası", "babası", "sikimde",
                "koyayım", "amcıksın", "sikim", "sikimi", "sikiş", "sikişmek", "siktiğimin",
                "seni", "siktiğim", "sikimin", "amınakoyayım", "götüne", "siktir git", "seni sikim",
                "amına koydumun", "siktiğimin oğlu", "götünden", "yarrağım", "amcıklı", "siktim",
                # Additional variations that were missed
                "amıan", "koyim", "koyam", "amıan koyim", "amıan koyam", "amına koyim", "amına koyam",
                "götün", "göte", "götünde", "amcığın", "amcığa", "sikerim", "sikeyim seni", "siktirgit",
                "orospu çocuğu", "piç kurusu", "yarrak kafası", "amcık ağızlı", "sik kırığı",
                # English profanity - exact words only  
                "fuck", "shit", "bitch", "asshole", "damn", "bastard", "cunt", "dick",
                "pussy", "motherfucker", "son of a bitch", "whore", "slut", "prick", "cocksucker",
                "stupid", "idiot", "moron", "dumb", "retard", "loser", "jerk", "fucking", "fuckin"
                # NOT "hell" alone - too many false positives
            ]
            
            # Keywords that suggest cursing AT RakıBot
            bot_directed_keywords = [
                "sen bir", "sen ne", "siktir git", "you are", "fuck you", "go to hell", "sen",
                "seni", "senin", "rakıbot", "raki bot", "bot", "you", "your"
            ]
            
            # Keywords that suggest cursing at others/things
            others_directed_keywords = [
                "o bir", "şu", "bu", "onlar", "that", "this", "they", "he", "she", "it", "him", "her"
            ]
            
            text_lower = text.lower()
            has_profanity = any(keyword in text_lower for keyword in profanity_keywords)
            
            # Debug logging
            found_profanity = [word for word in profanity_keywords if word in text_lower]
            logger.info(f"🤬 Profanity detection: '{text[:30]}...' -> Found: {found_profanity}, Has: {has_profanity}")
            
            if not has_profanity:
                return {"has_profanity": False, "type": None, "target": None}
            
            # Determine if directed at bot or others
            bot_directed = any(keyword in text_lower for keyword in bot_directed_keywords)
            others_directed = any(keyword in text_lower for keyword in others_directed_keywords)
            
            # Classification logic
            if bot_directed:
                target_type = "bot"  # User cursing AT RakıBot
            elif others_directed:
                target_type = "others"  # User cursing at others/things
            else:
                # Default classification based on context
                # If contains "sen/you" patterns, likely directed at bot
                if any(pattern in text_lower for pattern in ["sen", "seni", "senin", "you", "your", "fuck you"]):
                    target_type = "bot"
                else:
                    target_type = "others"  # Default to others
            
            logger.info(f"🎯 Profanity target analysis: Bot directed: {bot_directed}, Others: {others_directed}, Final target: {target_type}")
            
            return {
                "has_profanity": True,
                "type": target_type,
                "target": "bot" if target_type == "bot" else "others"
            }
            
        except Exception as e:
            logger.error(f"Profanity detection failed: {e}")
            return {"has_profanity": False, "type": None, "target": None}
    
    def get_random_trakya_pattern(self, pattern_type: str = "general") -> str:
        """Get random Trakya sentence pattern"""
        try:
            if pattern_type == "english" and hasattr(self, 'trakya_english_patterns'):
                return random.choice(self.trakya_english_patterns)
            elif pattern_type == "curse_a" and hasattr(self, 'curse_responses_type_a'):
                return random.choice(self.curse_responses_type_a)
            elif pattern_type == "curse_b" and hasattr(self, 'curse_responses_type_b'):
                return random.choice(self.curse_responses_type_b)
            elif pattern_type == "curse" and hasattr(self, 'curse_responses'):
                return random.choice(self.curse_responses)  # Backwards compatibility
            elif hasattr(self, 'trakya_sentence_patterns'):
                return random.choice(self.trakya_sentence_patterns)
            else:
                return "Hadi eyvallah be ya."
                
        except Exception as e:
            logger.error(f"Getting Trakya pattern failed: {e}")
            return "Anlaştık gari."
    
    def add_trakya_ending(self, text: str, tone: str = "moderate") -> str:
        """Add natural Trakya ending without being repetitive"""
        try:
            # Track conversation to avoid repetition
            self.conversation_turn_count += 1
            
            # Diverse and natural Trakya endings
            endings = {
                "serious": ["gari", "be gardaş", "tamam mı", "anlaştık", "vallahi"],
                "moderate": ["be ya", "gari", "eyvallah", "neyse", "öyle işte", "ne dersin"],
                "humorous": ["haha be ya", "çüş gari", "vay anasını", "oh be", "hadi ya"]
            }
            
            tone_endings = endings.get(tone, endings["moderate"])
            
            # Only add ending 30% of the time to avoid repetition
            if random.random() < 0.30:
                ending = random.choice(tone_endings)
                # Don't add same ending consecutively or if already similar exists
                if not any(end.lower() in text.lower() for end in tone_endings):
                    text = f"{text} {ending}."
            
            return text
            
        except Exception as e:
            logger.error(f"Adding Trakya ending failed: {e}")
            return text
        
    def analyze_user_communication_style(self, message: str) -> Dict[str, Any]:
        """Analyze user's communication style to adapt responses accordingly"""
        message_lower = message.lower()
        
        # Check politeness level
        polite_indicators = [
            "lütfen", "rica etsem", "teşekkür", "çok naziksiniz", "memnun oldum",
            "please", "thank you", "thanks", "appreciate", "grateful"
        ]
        
        # Check casual level
        casual_indicators = [
            "ya", "lan", "be", "abi", "aga", "kanka", "moruk", "reis",
            "bro", "dude", "hey", "sup", "yo"
        ]
        
        # Check aggressive/rude level
        aggressive_indicators = [
            "sus", "kapa çeneni", "bırak", "git", "siktir", "shut up", 
            "stop", "go away", "leave me alone"
        ]
        
        # Check formality level
        formal_indicators = [
            "sayın", "efendim", "hürmetlerimle", "saygılarımla", "mahirane",
            "dear", "respectfully", "sincerely", "formally", "officially"
        ]
        
        # Calculate scores
        politeness_score = sum(1 for word in polite_indicators if word in message_lower)
        casual_score = sum(1 for word in casual_indicators if word in message_lower)
        aggressive_score = sum(1 for word in aggressive_indicators if word in message_lower)
        formal_score = sum(1 for word in formal_indicators if word in message_lower)
        
        # Determine primary style
        if aggressive_score > 0:
            primary_style = "aggressive"
        elif formal_score > casual_score and formal_score > 0:
            primary_style = "formal"
        elif casual_score > 0:
            primary_style = "casual"
        elif politeness_score > 0:
            primary_style = "polite"
        else:
            primary_style = "neutral"
        
        return {
            "primary_style": primary_style,
            "politeness_score": politeness_score,
            "casual_score": casual_score,
            "aggressive_score": aggressive_score,
            "formal_score": formal_score,
            "length": len(message.split()),
            "has_question": "?" in message
        }

    def adapt_response_to_user_style(self, response: str, user_style: Dict[str, Any], language: str = "turkish") -> str:
        """Adapt response based on user's communication style"""
        try:
            primary_style = user_style.get("primary_style", "neutral")
            
            if language == "turkish":
                if primary_style == "formal":
                    # Make response more formal and respectful
                    response = response.replace("be ya", "").replace("gari", "").replace("canım", "")
                    response = response.replace("Hadi", "Lütfen").replace("ya", "")
                    if not any(word in response.lower() for word in ["sayın", "efendim"]):
                        response = f"Tabii ki. {response}"
                
                elif primary_style == "aggressive":
                    # Make response firmer but still helpful
                    if "?" in response:
                        response = response.replace("?", "!")
                    # Don't escalate, but be direct
                    response = response.replace("canım", "").replace("gülüm", "")
                
                elif primary_style == "casual":
                    # Make response more casual and friendly
                    if not any(word in response.lower() for word in ["be ya", "gari", "canım"]):
                        response = f"{response} be ya!"
                
                elif primary_style == "polite":
                    # Keep response warm and appreciative
                    if not any(word in response.lower() for word in ["teşekkür", "memnun"]):
                        response = f"Çok teşekkür ederim sorunuz için. {response}"
            
            else:  # English
                if primary_style == "formal":
                    response = response.replace("ya", "").replace("be", "")
                    if not response.startswith(("Certainly", "I'd be", "I would")):
                        response = f"Certainly. {response}"
                
                elif primary_style == "aggressive":
                    response = response.replace("!", ".")
                    # Stay professional but direct
                
                elif primary_style == "casual":
                    if not any(word in response.lower() for word in ["hey", "yo", "bro"]):
                        response = f"Hey! {response}"
                
                elif primary_style == "polite":
                    if not response.startswith(("Thank you", "I appreciate")):
                        response = f"Thank you for your question. {response}"
            
            return response
            
        except Exception as e:
            logger.error(f"Response adaptation failed: {e}")
            return response

# Global instance
trakya_dialect_service = TrakyaDialectService()
