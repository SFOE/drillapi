CANTONS = {
    "cantons_configurations": {
        "NE": {
            "active": False,
            "name": "NE",
            "ground_control_point": [
                [2555501, 1206134, 1, "OK"],
                [2556890, 1206292, 2, "RESTRICTION"],
            ],
            "wms_url": "https://sitn.ne.ch/mapserv_proxy?ogcserver=private-png",
            "query_url": "https://sitn.ne.ch/mapserv_proxy?ogcserver=private-png",
            "thematic_geoportal_url": "https://sitn.ne.ch/",
            "legend_url": "https://sitn.ne.ch/mapserv_proxy?ogcserver=private-png&cache_version=aba7524205e1498bb54f6c63b29dd14e&FORMAT=image%2Fpng&TRANSPARENT=true&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetLegendGraphic&LAYER=eg36_geotherm_carte_finale&SCALE=357142.1428571427",
            "info_format": "application/vnd.ogc.gml",
            "style": "",
            "layers": [
                {
                    "name": "eg38_geotherm_canepo_statut",
                    "property_name": "profondeur",
                    "property_values": [
                        {
                            "name": "mit Standardauflagen zulässig",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "mit spezifischen Auflagen zulässig",
                            "target_harmonized_value": 2,
                        },
                        {"name": "unzulässig", "target_harmonized_value": 3},
                    ],
                },
                {
                    "name": "eg37_geotherm_zones_exclues",
                    "property_name": "profondeur",
                    "property_values": [
                        {
                            "name": "mit Standardauflagen zulässig",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "mit spezifischen Auflagen zulässig",
                            "target_harmonized_value": 2,
                        },
                        {"name": "unzulässig", "target_harmonized_value": 3},
                    ],
                },
            ],
        },
        "JU": {
            "active": True,
            "name": "JU",
            "ground_control_point": [
                [2574738, 1249285, 1, "Autorisé"],
                [2576624, 1252365, 2, "A évaluer (prendre contact avec ENV)"],
                [
                    2588623,
                    1243355,
                    2,
                    "Autorisé avec restriction de profondeur de 150m",
                ],
                [
                    2588245,
                    1244475,
                    2,
                    "Autorisé avec restriction de profondeur de 100m",
                ],
                [2590205, 1244035, 2, "Autorisé avec restriction de profondeur de 70m"],
                [2573867, 1252854, 3, "Interdit"],
            ],
            "wms_url": "https://geoservices.jura.ch/wms",
            "query_url": "https://geoservices.jura.ch/wms",
            "thematic_geoportal_url": "https://geo.jura.ch/theme/POI?lang=fr&map_x=2580390&map_y=1242845&map_zoom=1&tree_groups=Geologie%2CPoint%20d%27interets%20-%20Exclusive&tree_group_layers_Point%20d%27interets%20-%20Exclusive=sdt_09_08_fermeture_provisoire%2Cpoc_20_03_points_rencontre_urgence%2Crea_19_03_defibrillateurs%2Csdt_17_01_points_interets_administration&baselayer_ref=sdt_01_03_mensuration_officielle&baselayer_opacity=0&tree_enable_env_18_06_cadastre_geologique=false&tree_enable_env_18_03_geothermie_limitation_forages_sondes_geothermiques=true",
            "legend_url": "https://geoservices.jura.ch/wms?version=1.3.0&service=WMS&request=GetLegendGraphic&sld_version=1.1.0&layer=ju.env_18_03_geothermie_limitation_forages_sondes_geothermiques&format=image/png&STYLE=default",
            "info_format": "application/vnd.ogc.gml",
            "style": "",
            "layers": [
                {
                    "name": "ju.env_18_03_geothermie_limitation_forages_sondes_geothermiques",
                    "property_name": "limitation_forage",
                    "property_values": [
                        {
                            "name": "Autorisé",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "A évaluer (prendre contact avec ENV)",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "Autorisé avec restriction de profondeur de 150m",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "Autorisé avec restriction de profondeur de 100m",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "Autorisé avec restriction de profondeur de 70m",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "Interdit",
                            "target_harmonized_value": 3,
                        },
                    ],
                },
            ],
        },
        "ZH": {
            "active": True,
            "name": "ZH",
            "ground_control_point": [
                [2674790, 1259760, 2, "Auflagen & waermenutzung-zone-d"],
                [2689003, 1274084, 3, "waermenutzung-zone-a"],
                [2681001, 1260920, 3, "waermenutzung-zone-b"],
                [2689003, 1274084, 3, "waermenutzung-zone-c"],
                [2684610, 1256659, 3, "waermenutzung-zone-d"],
                [2684909, 1249849, 3, "waermenutzung-zone-e"],
                [2684200, 1244025, 1, "waermenutzung-zone-f"],
            ],
            "wms_url": "https://wms.zh.ch/AwelGSWaermewwwZHWMS",
            "query_url": "https://wms.zh.ch/AwelGSWaermewwwZHWMS",
            "thematic_geoportal_url": "https://maps.zh.ch/?topic=AwelGSWaermewwwZH&x=2685104.6444391827&y=1252283.9396742217&scale=70517.93063503089",
            "legend_url": "",
            "info_format": "application/vnd.ogc.gml",
            "style": "",
            "layers": [
                {
                    "name": "erdwaermesonden-auflagen",
                    "property_name": "zonen",
                    "property_values": [
                        {"name": "undefined", "target_harmonized_value": 0},
                        {"name": "Auflagen", "target_harmonized_value": 1},
                        {"name": "Verbot", "target_harmonized_value": 2},
                    ],
                },
                {
                    "name": "waermenutzung-zone-a",
                    "property_name": "geodb_oid",
                    "target_harmonized_value": 10,
                },
                {
                    "name": "waermenutzung-zone-b",
                    "property_name": "geodb_oid",
                    "target_harmonized_value": 20,
                },
                {
                    "name": "waermenutzung-zone-c",
                    "property_name": "geodb_oid",
                    "target_harmonized_value": 30,
                },
                {
                    "name": "waermenutzung-zone-d",
                    "property_name": "geodb_oid",
                    "target_harmonized_value": 40,
                },
                {
                    "name": "waermenutzung-zone-e",
                    "property_name": "geodb_oid",
                    "target_harmonized_value": 50,
                },
                {
                    "name": "waermenutzung-zone-f",
                    "property_name": "geodb_oid",
                    "target_harmonized_value": 60,
                },
            ],
            "harmonyMap": [
                {"sum": 10, "value": 3},
                {"sum": 11, "value": 3},
                {"sum": 12, "value": 3},
                {"sum": 20, "value": 3},
                {"sum": 21, "value": 3},
                {"sum": 22, "value": 3},
                {"sum": 32, "value": 3},
                {"sum": 42, "value": 3},
                {"sum": 52, "value": 3},
                {"sum": 62, "value": 3},
                {"sum": 30, "value": 2},
                {"sum": 31, "value": 2},
                {"sum": 41, "value": 2},
                {"sum": 50, "value": 2},
                {"sum": 51, "value": 2},
                {"sum": 61, "value": 2},
                {"sum": 40, "value": 1},
                {"sum": 60, "value": 1},
            ],
        },
        "ZG": {
            "active": True,
            "name": "ZG",
            "ground_control_point": [
                [2676912, 1228091, 1, "mit Standardauflagen zulässig"],
                [2684565, 1225437, 2, "mit spezifischen Auflagen zulässig"],
                [2686680, 1226360, 3, "unzulässig"],
                [2690680, 1219207, 4],  # Middle of the lake => empty features
            ],
            "wms_url": "https://services.geo.zg.ch/ows/Erdwaermenutzung",
            "query_url": "https://services.geo.zg.ch/ows/Erdwaermenutzung",
            "legend_url": "",
            "thematic_geoportal_url": "https://zugmap.ch/bmcl/?project=ZugMap.ch&legend=alle%20Themen&rotation=0.00&scale=26941&center=2681358,1225229&layers=6585bde8-1bc8-499c-a4b8-21ec30a0e426",
            "info_format": "application/vnd.ogc.gml",
            "style": "default",
            "layers": [
                {
                    "name": "zg.ews_zulaessigkeit",
                    "property_name": "zulaessigkeit",
                    "property_values": [
                        {
                            "name": "mit Standardauflagen zulässig",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "mit spezifischen Auflagen zulässig",
                            "target_harmonized_value": 2,
                        },
                        {"name": "unzulässig", "target_harmonized_value": 3},
                    ],
                }
            ],
        },
        "VS": {
            "active": True,
            "name": "VS",
            "ground_control_point": [
                [2596336, 1122359, 1, "CLASSGV 1"],
                [2598146, 1124454, 1, "CLASSGV 2"],
                [
                    2598043,
                    1123873,
                    3,
                    "CLASSGV 4",
                ],  # REST response is CLASSGV 4. Clarify classification with VS
                [2597117, 1120835, 3, "CLASSGV 4"],
                [2598068.4, 1130927.1, 4, "CLASSGV 5"],
            ],
            "wms_url": "https://sit.vs.ch/arcgis/services/ENVIRONNEMENT/MapServer/WMSServer",
            "query_url": "https://sit.vs.ch/arcgis/services/ENVIRONNEMENT/MapServer/WMSServer",
            "legend_url": "https://sit.vs.ch/arcgis/services/ENVIRONNEMENT/MapServer/WMSServer?request=GetLegendGraphic%26version=1.3.0%26format=image/png%26layer=29",
            "thematic_geoportal_url": "https://sitonline.vs.ch/environnement/eso_admissibilite_PAC/#/?lang=fr",
            "info_format": "application/geo+json",
            "style": "",
            "layers": [
                {
                    "name": "29",
                    "rootName": "features",
                    "nodeName": "attributes",
                    "property_name": "CLASSGV",
                    "property_values": [
                        {
                            "name": "1",
                            "desc": "Sondes géothermiques admises (max. 200 m sans étude)",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "2",
                            "desc": "Sondes géothermiques limitées à 100 m de profondeur",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "3",
                            "desc": "Au cas par cas - Etude préalable (contacter le SEN)",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "4",
                            "desc": "Sondes géothermiques interdites",
                            "target_harmonized_value": 3,
                        },
                        {
                            "name": "5",
                            "desc": "Hors zone (contacter le SEN)",
                            "target_harmonized_value": 3,
                        },
                    ],
                }
            ],
        },
        "VD": {
            "active": True,
            "name": "VD",
            "ground_control_point": [
                [2536682, 1156974, 1, "Admissible sous conditions"],
                [2548704, 1168639, 2, "Limitation"],
                [2535551, 1180721, 3, "Interdiction"],
                [2535239, 1148966, 4],  # Middle of the lake, empty feature
            ],
            "wms_url": "https://www.ogc.vd.ch/public/services/OGC/wmsVD/Mapserver/WMSServer",
            "query_url": "https://www.ogc.vd.ch/public/services/OGC/wmsVD/Mapserver/WMSServer",
            "legend_url": "https://www.ogc.vd.ch/public/services/OGC/wmsVD/Mapserver/WMSServer?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetLegendGraphic&FORMAT=image%2Fpng&LAYER=vd.admissibilite_indicative_sonde_geothermique",
            "thematic_geoportal_url": "https://www.geo.vd.ch/?visiblelayers=%7B%22GEO_THEME_ENERG%22%3A%5B%22Potentiel%20thermique%20global%22%2C%22Type%20de%20site%22%5D%7D&share=4c196dee-a011-479e-abd1-2a805f1b34a3",
            "info_format": "application/geo+json",
            "style": "",
            "layers": [
                {
                    "name": "vd.admissibilite_indicative_sonde_geothermique",
                    "property_name": "Type",
                    "property_values": [
                        {
                            "name": "Admissible sous conditions",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "Admissible aux conditions standard, jusqu’à 300 mètres",
                            "target_harmonized_value": 1,
                        },
                        {"name": "Limitation", "target_harmonized_value": 2},
                        {
                            "name": "Limitation, soumis à des conditions spéciales",
                            "target_harmonized_value": 2,
                        },
                        {"name": "Interdiction", "target_harmonized_value": 3},
                    ],
                }
            ],
        },
        "UR": {
            "style": "",
            "active": True,
            "name": "UR",
            "ground_control_point": [
                [2703052, 1180378, 1, "B"],
                [2699152, 1175536, 2, "C"],
                [2689034, 1196007, 3, "A"],
            ],
            "wms_url": "https://geo.ur.ch/webmercator/wms",
            "query_url": "https://geo.ur.ch/webmercator/wms",
            "legend_url": "",
            "thematic_geoportal_url": "https://geo.ur.ch/?center=962589%2C5922132&layers=Zul%C3%A4ssigkeit%20Grundwasserw%C3%A4rmepumpen&opacity=0.3&visibility=true&zoom=12",
            "info_format": "application/vnd.ogc.gml",
            "style": "",
            "style": "",
            "layers": [
                {
                    "name": "umwelt:wnk_zulaessigkeitsbereiche_erdsonden",
                    "property_name": "zulaessigkeit_ews",
                    "property_values": [
                        {
                            "name": "B",
                            "desc": "grüner Zulässigkeitsbereich",
                            "desc2": "Zulässig unter allgemeinen Auflagen",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "C",
                            "desc": "gelber Zulässigkeitsbereich",
                            "desc2": "Zulässig unter zusätzlichen Schutzmassnahmen",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "A",
                            "desc": "roter Zulässigkeitsbereich / nicht zulässig",
                            "desc2": "Nicht zulässig",
                            "target_harmonized_value": 3,
                        },
                    ],
                }
            ],
        },
        "TI": {
            "active": True,
            "name": "TI",
            "ground_control_point": [[2715738, 1125797, 3], [2712602, 1133130, 1]],
            "wms_url": "https://wms.geo.ti.ch/service",
            "query_url": "https://wms.geo.ti.ch/service",
            "legend_url": "https://www4.ti.ch/fileadmin/GENERALE/IGDAC/ccgeo/legends/ac_059_1_v1_0/ac_059_1_v1_0_idoneita_sonde_geotermiche_.png",
            "thematic_geoportal_url": "https://map.geo.ti.ch/?lang=it&baselayer_ref=Carta%20Nazionale%20%28bianco%20e%20nero%29&tree_group_layers_Idoneit%C3%A0%20sonde%20geotermiche=Idoneit%C3%A0%20sonde%20geotermiche&tree_groups=Idoneit%C3%A0%20sonde%20geotermiche",
            "info_format": "application/vnd.ogc.gml",
            "style": "",
            "layers": [
                {
                    "name": "ac_059_1_v1_0_idoneita_sonde_geotermiche",
                    "property_name": "idoneita_desc",
                    "property_values": [
                        {
                            "name": "In linea di principio non permesso",
                            "desc": "nicht zulässig",
                            "target_harmonized_value": 3,
                        },
                        {
                            "name": "In linea di principio permesso con condizioni",
                            "desc": "bedingt zulässig",
                            "target_harmonized_value": 1,
                        },
                    ],
                }
            ],
        },
        "TG": {
            "active": True,
            "name": "TG",
            "ground_control_point": [
                [2747716.6, 1262056.4, 3, "EWS grundsätzlich unzulässig"],
                [
                    2747720.5,
                    1262436.9,
                    1,
                    "EWS grundsätzlich zulässig mit Standardauflagen",
                ],
                [
                    2709370.0,
                    1268975.0,
                    2,
                    "EWS grundsätzlich zulässig mit zusätzlichen Auflagen",
                ],
                [2712450.0, 1269125.0, 1, "EWS grundsätzlich zulässig"],
            ],
            "wms_url": "https://ows.geo.tg.ch/geofy_access_proxy/erdwaerme",
            "query_url": "https://ows.geo.tg.ch/geofy_access_proxy/erdwaerme",
            "legend_url": "https://map.geo.tg.ch/services/geofy_chsdi3/static/images/legends/erdwaerme_eignung_de.png",
            "thematic_geoportal_url": "https://map.geo.tg.ch/apps/mf-geoadmin3/?lang=de&topic=geologieboden&E=2718775.00&N=1270425.00&zoom=1&layers_opacity=1,1,0.9&layers=erdwaerme_eignung,erdwaerme_erdwaermesondenbohrungen,grundwasserkarte-fassung",
            "info_format": "application/vnd.ogc.gml",
            "style": "",
            "layers": [
                {
                    "name": "Eignungszonen",
                    "property_name": "eignungszone",
                    "property_values": [
                        {
                            "name": "1",
                            "desc": "EWS grundsätzlich zulässig mit Standardauflagen",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "2",
                            "desc": "EWS grundsätzlich zulässig mit Standardauflagen",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "3",
                            "desc": "EWS grundsätzlich unzulässig, Grundwasserschutzzone",
                            "target_harmonized_value": 3,
                        },
                    ],
                }
            ],
        },
        "SZ": {
            "active": True,
            "name": "SZ",
            "ground_control_point": [
                [2707885, 1226453, 1],
                [2707994, 1227010, 2],
                [2708393, 1227843, 3],
            ],
            "wms_url": "https://map.geo.sz.ch/mapserv_proxy",
            "query_url": "https://map.geo.sz.ch/mapserv_proxy",
            "legend_url": "",
            "thematic_geoportal_url": "https://map.geo.sz.ch/?lang=fr&map_x=2697700&map_y=1213275&map_zoom=0&baselayer_ref=Landeskarte%20(farbig)&tree_groups=grp_Energie_Erdw%C3%A4rmenutzung%2Cgrp_Energie_Frei_Leitungskataster%2Cgrp_Energie_Netzgebiete%2Cgrp_Energie_Solarenergie%2Cgrp_Energie_Wasserw%C3%A4rmenutzung&tree_group_layers_grp_Energie_Erdw%C3%A4rmenutzung=ch.sz.a034c.waermenutzung.erdwaermeanlage.erdwaermesonde%2Cch.sz.a034c.waermenutzung.erdwaermeanlage.erdwaermesonde_nicht_bewilligungsfaehig%2Cch.sz.a034c.waermenutzung.erdwaermeanlage.energiepfahl%2Cch.sz.a034c.waermenutzung.erdwaermeanlage.energiekorb%2Cch.sz.a034c.waermenutzung.erdwaermeanlage.erdregister%2Cch.sz.a034c.waermenutzung.erdwaerme",
            "info_format": "application/vnd.ogc.gml",
            "style": "",
            "layers": [
                {
                    "name": "ch.sz.a034c.waermenutzung.erdwaerme.technisch",
                    "property_name": "zulaessigkeit_cd",
                    "property_values": [
                        {
                            "name": "ja",
                            "desc": "zulässig",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "Abklaerung_noetig",
                            "desc": "bedingt zulässig",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "nein",
                            "desc": "nicht zulässig",
                            "target_harmonized_value": 3,
                        },
                    ],
                }
            ],
        },
        "SH": {
            "active": True,
            "name": "SH",
            "ground_control_point": [
                [2690343, 1289821, 1, "3"],
                [2682889, 1292346, 2, "5"],
                [2691554, 1293373, 3, "1"],
                [2695085, 1290396, 2, "41"],
                [2695476, 1286474, 2, "42"],
            ],
            "wms_url": "https://wms.geo.sh.ch/wms",
            "query_url": "https://wms.geo.sh.ch/wms",
            "legend_url": "",
            "thematic_geoportal_url": "https://map.geo.sh.ch/geoportal/?project=Geoportal%20Schaffhausen&legend=Legende&rotation=0.00&scale=90202&center=2692188,1282000&layers=0bf7129c-2c80-4371-941f-556c4a6ba1f1",
            "info_format": "application/vnd.ogc.gml",
            "style": "",
            "layers": [
                {
                    "name": "sh.energie.erdsonden.eignung",
                    "property_name": "eignung_erdwaermesonden_code",
                    "property_values": [
                        {
                            "name": "3",
                            "desc": "EWS bis 200 m Tiefe zulässig (über 200 m Vorabklärung notwendig)",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "5",
                            "desc": "EWS mit Vorabklärung und fallweise geologischer Begleitung zulässig",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "41",
                            "desc": "GWWN-Grossanlagen mit Gutachten zulässig (EWS auf Anfrage)",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "42",
                            "desc": "GWWN-Grossanlagen mit Gutachten zulässig (Kurzsonden auf Anfrage)",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "1",
                            "desc": "EWS und GWWN unzulässig",
                            "target_harmonized_value": 3,
                        },
                    ],
                }
            ],
        },
        "SG": {
            "active": True,
            "name": "SG",
            "ground_control_point": [
                [2733447, 1241435, 2, "1"],
                [2735185, 1244058, 1, "3"],
                [2742740, 1233995, 3, "2"],
            ],
            "wms_url": "https://services.geo.sg.ch/wss/service/SG00025_WMS/guest",
            "query_url": "https://services.geo.sg.ch/wss/service/SG00025_WMS/guest",
            "legend_url": "",
            "thematic_geoportal_url": "https://www.geoportal.ch/ktsg/map/29?y=2743944.00&x=1231900.00&scale=300000&rotation=0",
            "info_format": "application/geo+json",
            "style": "",
            "layers": [
                {
                    "name": "Zulaessigkeitsbereich",
                    "property_name": "OBJECTID",
                    "property_values": [
                        {
                            "name": "2",
                            "desc": "nicht zulässig (siehe Erläuterungen)",
                            "target_harmonized_value": 3,
                        },
                        {
                            "name": "3",
                            "desc": "zulässig (siehe Erläuterungen)",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "1",
                            "desc": "bedingt zulässig (siehe Erläuterungen)",
                            "target_harmonized_value": 2,
                        },
                    ],
                }
            ],
        },
        "OW": {
            "active": True,
            "name": "OW",
            "ground_control_point": [
                [2664351, 1193538, 1, "zulaessig"],
                [2660898, 1191688, 1, "Auflage_GewaesserschutzbereichAu"],
                [2660281, 1190191, 2, "Auflage_NutzungsgebietGrundwasser"],
                [2661431, 1192803, 2, "Auflage_bedingtzulaessig"],
                [2661534, 1193397, 3, "nichtzulaessig"],
                [2657375.6, 1180366.4, 3, "Gebiete_mit_potentieller_Verkarstung"],
            ],
            "wms_url": "https://www.gis-daten.ch/wms/bfe_kann_ich_bohren/service",
            "query_url": "https://www.gis-daten.ch/wms/bfe_kann_ich_bohren/service",
            "legend_url": "",
            "thematic_geoportal_url": "https://www.gis-daten.ch/map/ow_waermenutzung",
            "info_format": "application/json",
            "style": "",
            "layers": [
                {
                    "name": "ch.ow.ews_zulaessigkeit",
                    "rootName": "features",
                    "nodeName": "properties",
                    "property_name": "Zulaessigkeit",
                    "property_values": [
                        {
                            "name": "zulaessig",
                            "desc": "Wärmenutzung zulässig (Bewilligungspflicht)",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "Auflage_GewaesserschutzbereichAu",
                            "desc": "Wärmenutzung zulässig (Bewilligungspflicht)",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "Auflage_NutzungsgebietGrundwasser",
                            "desc": "Wärmenutzung zulässig (Bewilligungspflicht); Geologische Begleitung während der Bohrung erforderlich",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "Auflage_bedingtzulaessig",
                            "desc": "Wärmenutzung bedingt zulässig (Bewilligungspflicht); vorgängiges geologisches Gutachten erforderlich als Grundlage zur Prüfung der Bewilligungsfähigkeit",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "nichtzulaessig",
                            "desc": "Wärmenutzung nicht zulässig",
                            "target_harmonized_value": 3,
                        },
                        {
                            "name": "Gebiete_mit_potentieller_Verkarstung",
                            "desc": "Wärmenutzung nicht zulässig",
                            "target_harmonized_value": 3,
                        },
                    ],
                }
            ],
        },
        "NW": {
            "active": True,
            "name": "NW",
            "ground_control_point": [
                [2671744, 1196809, 3, "bautechnisch_bauverbot"],
                [2675123, 1198890, 3, "Trinkwasserschutzgebiet"],
                [2672327, 1202452, 3, "nutzbare_Grundwassergebiete"],
                [2668633, 1202922, 2, "bebaubares_Grundwassergebiet"],
                [2668267, 1201091, 2, "vermutlich_unproblematisch"],
                [2668945, 1200200, 2, "problematisch"],
                [2668854, 1199481, 2, "bautechnisch_problematisch"],
                [2669798, 1200979, 1, "unproblematisch"],
            ],
            "wms_url": "https://www.gis-daten.ch/wms/bfe_kann_ich_bohren/service",
            "query_url": "https://www.gis-daten.ch/wms/bfe_kann_ich_bohren/service",
            "legend_url": "",
            "thematic_geoportal_url": "https://www.gis-daten.ch/map/nw_waermenutzung",
            "info_format": "application/json",
            "style": "",
            "layers": [
                {
                    "name": "ch.nw.waermenutzungsbereiche",
                    "rootName": "features",
                    "nodeName": "properties",
                    "property_name": "Art",
                    "property_values": [
                        {
                            "name": "bautechnisch_bauverbot",
                            "desc": "Wärmenutzung aus dem Untergrund verboten",
                            "target_harmonized_value": 3,
                        },
                        {
                            "name": "Trinkwasserschutzgebiet",
                            "target_harmonized_value": 3,
                        },
                        {
                            "name": "nutzbare_Grundwassergebiete",
                            "desc": "Grundwassergebiet mit Erdsondenverbot",
                            "target_harmonized_value": 3,
                        },
                        {
                            "name": "bebaubares_Grundwassergebiet",
                            "desc": "Grundwassergebiet ohne Erdsondenverbot",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "vermutlich_unproblematisch",
                            "desc": "Vermutlich unproblematische Untergrundverhältnisse",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "problematisch",
                            "desc": "Unsichere Untergrundverhältnisse",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "bautechnisch_problematisch",
                            "desc": "Bautechnisch problematische Untergrundverhältnisse",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "unproblematisch",
                            "desc": "Unproblematische Untergrundverhältnisse",
                            "target_harmonized_value": 1,
                        },
                    ],
                }
            ],
        },
        "LU": {
            "active": True,
            "name": "LU",
            "ground_control_point": [
                [2665393, 1217714, 1, "ews_zulaessig"],
                [2652462, 1196901, 2, "ews_zulaessig & ews_zulaessig_auflagen"],
                [2651972, 1200000, 3, "ews_nicht_zulaessig & ews_zulaessig_auflagen"],
                [
                    2645371,
                    1200735,
                    2,
                    "ews_vorabklaeren",
                ],  # TODO: check with LU how to map lanslide areas
                [2645598, 1202446, 3, "ews_nicht_zulaessig"],
            ],
            "wms_url": "https://public.geo.lu.ch/ogd/services/managed/EWNUTZXX_COL_V3_MP/MapServer/WMSServer",
            "query_url": "https://public.geo.lu.ch/ogd/services/managed/EWNUTZXX_COL_V3_MP/MapServer/WMSServer",
            "legend_url": "https://github.com/SFOE/SuitabilityGeothermalDrillingSwitzerland/raw/main/images/legend_lu.png",
            "thematic_geoportal_url": "https://map.geo.lu.ch/gebaeudeenergie/erdwaerme/",
            "info_format": "application/geo+json",
            "style": "",
            "loopLayers": True,
            # no property values for this canton, only layers are matched if request hits a polygon
            "layers": [
                {
                    "name": "3",
                    "desc": "ews_zulaessig",
                    "property_name": "Erdwärmenutzung zulässig",
                    "target_harmonized_value": 1,
                },
                {
                    "name": "1",
                    "desc": "ews_vorabklaeren",
                    "property_name": "Erdwärmenutzung zulässig mit Auflagen",
                    "target_harmonized_value": 2,
                },
                {
                    "name": "2",
                    "desc": "ews_zulaessig_auflagen",
                    "property_name": "Erdwärmenutzung zulässig mit Auflagen",
                    "target_harmonized_value": 2,
                },
                {
                    "name": "0",
                    "desc": "ews_nicht_zulaessig",
                    "property_name": "Erdwärmenutzung nicht zulässig",
                    "target_harmonized_value": 3,
                },
            ],
            "harmonyMap": [
                {"sum": 1, "value": 1},
                {"sum": 2, "value": 2},
                {"sum": 11, "value": 2},
                {"sum": 12, "value": 2},
                {"sum": 13, "value": 3},
                {"sum": 3, "value": 3},
            ],
        },
        "GR": {
            "active": True,
            "name": "GR",
            "ground_control_point": [
                [2745188, 1187042, 1, "zulässig"],
                [2747613, 1190056, 2, "bedingt zulässig"],
                [2730752, 1191438, 3, "nicht zulässig"],
            ],
            "wms_url": "https://wms.geo.gr.ch/erdwaermenutzung",
            "query_url": "https://wms.geo.gr.ch/erdwaermenutzung",
            "legend_url": "https://map.geo.gr.ch/mapserv_proxy?ogcserver=Kanton+Graub%C3%BCnden%2C+Energie&cache_version=6cf674ab2fb648a0ac60156e614e4bbe&FORMAT=image%2Fpng&TRANSPARENT=true&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetLegendGraphic&LAYERTITLE=FALSE&Itemfontsize=10&LAYER=uGSP_Zulaessigkeit&SCALE=499998.9999999998",
            "thematic_geoportal_url": "https://map.geo.gr.ch/public/theme/uGSP_Energie?tree_group_layers_layer4gmf24.uGSP_Grundstueckabfrage_Grundstueckabfrage_AGGR=layer4gmf24.uGSP_Grundstueckabfrage_AGGR&lang=fr&map_x=2760071&map_y=1169982&map_zoom=1&baselayer_ref=Karte%20grau&tree_group_layers_uGSP_Nutzungsplanung_Kommunaler_Darstellungsdienst.uGSP_Nutzungsplanung_Genereller_Erschliessungsplan=uGSP_Nutzungsplanung_Kommunaler_Darstellungsdienst.uGSP_GEP_Energie_AGGR&theme=uGSP_Energie&tree_groups=uGSP_Energie_Waermepumpen_Netzgebiete_Globalstrahlung_WWK.uGSP_Globalstrahlung_jaehrlich%2CuGSP_Energie_Waermepumpen_Netzgebiete_Globalstrahlung_WWK.uGSP_Globalstrahlung_Vollzug%2CuGSP_Energie_Waermepumpen_Netzgebiete_Globalstrahlung_WWK.uGSP_Netzgebiet_Elektroversorgung_AGGR%2CuGSP_Energie.uGSP_Erdwaermenutzung%2CuGSP_Energie_Waermepumpen_Netzgebiete_Globalstrahlung_WWK.uGSP_Waermepumpe_Luft_Wasser%2CuGSP_Energie_Waermepumpen_Netzgebiete_Globalstrahlung_WWK.uGSP_Wasserwerkkataster_AGGR%2Clayer4gmf24.uGSP_Grundstueckabfrage_Grundstueckabfrage_AGGR&tree_group_layers_uGSP_Energie.uGSP_Erdwaermenutzung=uGSP_Energie.uGSP_Zulaessigkeit",
            "info_format": "application/vnd.ogc.gml",
            "style": "",
            "layers": [
                {
                    "name": "Erdwaermenutzung_Zulaessigkeit",
                    "property_name": "zulaessigkeit",
                    "property_values": [
                        {"name": "zulässig", "target_harmonized_value": 1},
                        {"name": "bedingt zulässig", "target_harmonized_value": 2},
                        {"name": "nicht zulässig", "target_harmonized_value": 3},
                    ],
                }
            ],
        },
        "GL": {
            "active": True,
            "name": "GL",
            "ground_control_point": [
                [2724237, 1206147, 3, "Erdsondenausschlussgebiet"],
                [2725831, 1215961, 4, "undefined"],
            ],
            "wms_url": "https://wms.geo.gl.ch/",
            "query_url": "https://wms.geo.gl.ch/",
            "legend_url": "https://map.geo.gl.ch/api/v1/legend/mainmap?VERSION=1.3.0&SERVICE=WMS&REQUEST=GetLegendGraphic&FORMAT=image%2Fpng&CRS=EPSG%3A2056&SRS=EPSG%3A2056&SLD_VERSION=1.1.0&WIDTH=200&HEIGHT=200&LAYER=ch.gl.utilities.erdsondenausschlussbereich&FILTER=",
            "thematic_geoportal_url": "https://map.geo.gl.ch/?t=default&l=ch.gl.utilities.erdsondenausschlussbereich%2Cch.gl.basemaps.kantonsmaske%5B40%5D&bl=pixelkarte&c=2726296%2C1208537&s=40000",
            "info_format": "application/vnd.ogc.gml",
            "style": "",
            "layers": [
                {
                    "name": "ch.gl.utilities.erdsondenausschlussbereich",
                    "property_name": "art",
                    "property_values": [
                        {"name": "undefined", "target_harmonized_value": 2},
                        {
                            "name": "Erdsondenausschlussgebiet",
                            "target_harmonized_value": 3,
                        },
                    ],
                }
            ],
        },
        "GE": {
            "active": True,
            "name": "GE",
            "ground_control_point": [
                [
                    2510785,
                    1121097,
                    1,
                    "Sondes géothermiques verticales (système fermé)",
                ],
                [2506500, 1118148, 2, "Demande de renseignement"],
                [2502640, 1113946, 3, "Interdiction de géothermie"],
                [2494984, 1116373, 3, "Géothermie sur nappe (système ouvert)"],
            ],
            "wms_url": "https://app2.ge.ch/tergeoservices/rest/services/Hosted/GOL_EXPLOITATION_GEOTHERMIE/MapServer",
            "query_url": "https://app2.ge.ch/tergeoservices/rest/services/Hosted/GOL_EXPLOITATION_GEOTHERMIE/FeatureServer",
            "legend_url": "",
            "style": "",
            "thematic_geoportal_url": "https://map.sitg.ge.ch/app/?portalresources=GOL_EXPLOITATION_GEOTHERMIE",
            "info_format": "arcgis/json",
            "layers": [
                {
                    "id": 0,
                    "name": "GOL_EXPLOITATION_GEOTHERMIE",
                    "rootName": "features",
                    "nodeName": "attributes",
                    "property_name": "secteur",
                    "property_values": [
                        {
                            "name": "Sondes géothermiques verticales (système fermé)",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "Demande de renseignement",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "Interdiction de géothermie",
                            "target_harmonized_value": 3,
                        },
                        {
                            "name": "Géothermie sur nappe (système ouvert)",
                            "target_harmonized_value": 3,
                        },
                    ],
                }
            ],
        },
        "FR": {
            "active": True,
            "name": "FR",
            "ground_control_point": [
                [2582124, 1164966, 1, "SGV autorisées"],
                [2582392, 1164789, 2, "SGV avec demande préalable obligatoire"],
                [2582439, 1165031, 3, "SGV interdites"],
            ],
            # Base MapServer URL (layer = 17)
            "wms_url": "https://map.geo.fr.ch/arcgis/rest/services/PortailCarto/Theme_environnement/MapServer",
            "query_url": "https://map.geo.fr.ch/arcgis/rest/services/PortailCarto/Theme_environnement/MapServer",
            "legend_url": "",
            "thematic_geoportal_url": "https://map.geo.fr.ch/?share=a526a596-5cde-491e-b22d-6d692e78f25b",
            "info_format": "arcgis/json",
            "style": "",
            "layers": [
                {
                    "id": 17,  # Required: ESRI REST layer ID
                    "name": "Admissibilite_SGV",
                    "desc": "Admissibilite des sondes geothermiques SGV",
                    "rootName": "features",
                    "rootName2": "results",
                    "nodeName": "attributes",
                    "property_name": "DA_SGV_DESC",
                    "property_name2": "Admissibilité",
                    "property_values": [
                        {"name": "SGV autorisées", "target_harmonized_value": 1},
                        {
                            "name": "SGV avec demande préalable obligatoire",
                            "target_harmonized_value": 2,
                        },
                        {"name": "SGV interdites", "target_harmonized_value": 3},
                    ],
                }
            ],
        },
        "BL": {
            "active": True,
            "name": "BL",
            "ground_control_point": [
                [2622256, 1258565, 1, "BC"],
                [2623503, 1259120, 2, "B"],
                [2620984, 1259551, 4, "nB"],
                [2620314.1, 1263004.5, 1, "C"],
                [2623369, 1261302, 3, "undefined", "Fall A"],
            ],
            "wms_url": "https://geowms.bl.ch/",
            "query_url": "https://geowms.bl.ch/",
            "legend_url": "https://geoview.bl.ch/main/wsgi/mapserv_proxy?cache_version=5d00dfedcd27448bbae53376d44c94e1&FORMAT=image%2Fpng&TRANSPARENT=TRUE&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetLegendGraphic&EXCEPTIONS=application%2Fvnd.ogc.se_xml&LAYER=erdwaerme_uebersicht_group&SCALE=188975.99999999997",
            "thematic_geoportal_url": "https://geoview.bl.ch/?map_x=2632500&map_y=1245475&map_zoom=2&tree_group_layers_Oberfl%C3%A4chennahe%20Erdw%C3%A4rme=erdwaerme_uebersicht_group&tree_groups=Oberfl%C3%A4chennahe%20Erdw%C3%A4rme",
            "info_format": "application/vnd.ogc.gml",
            "style": "",
            "layers": [
                {
                    "name": "erdwaerme_uebersicht_ohne_a",
                    "property_name": "ov_kategor",
                    "property_values": [
                        {
                            "name": "C",
                            "desc": "Fall C - Wärmenutzung durch Erdwärmesonden bis max. zulässige Bohrtiefe mit Standardauflagen möglich",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "B",
                            "desc": "Fall B - Wärmenutzung durch Erdwärmesonden mit speziellen Auflagen möglich",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "BC",
                            "desc": "Fall BC - Wärmenutzung durch Erdwärmesonden mit Standardauflagen für Schichten des Fall C, darunter bis max. zulässige Bohrtiefe Wärmenutzung mit spez. Auflagen",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "nB",
                            "desc": "Fall nB - Gebiet wurde noch nicht bearbeitet",
                            "target_harmonized_value": 4,
                        },
                        {
                            "name": "undefined",
                            "desc": "Fall A - Wärmenutzung durch Erdwärmesonden unzulässig",
                            "target_harmonized_value": 3,
                        },
                    ],
                }
            ],
        },
        "BE": {
            "active": True,
            "name": "BE",
            "ground_control_point": [
                [2599525, 1201544, 1, "1"],
                [2597320, 1198900, 1, "2"],
                [2599516, 1200212, 2, "3"],
                [2600318, 1199065, 3, "4"],
                [2621040, 1171911, 4, "undefined", "im Thunersee"],
            ],
            "wms_url": "https://www.geoservice.apps.be.ch/geoservice3/services/a42geo/of_utilitiescommunication01_de_ms_wms/MapServer/WMSServer",
            "query_url": "https://www.geoservice.apps.be.ch/geoservice3/services/a42geo/of_utilitiescommunication01_de_ms_wms/MapServer/WMSServer",
            "legend_url": "",
            "thematic_geoportal_url": "https://www.topo.apps.be.ch/pub/map/?lang=de&gpk=ERDSOND_GPK",
            "info_format": "application/geo+json",
            "style": "",
            "layers": [
                {
                    "name": "ERDSOND_ERDSOND_VW_16828",
                    "property_name": "CODE",
                    "property_values": [
                        {
                            "name": "1",
                            "desc": "Erdwärmesonden erlaubt",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "2",
                            "desc": "Erdwärmesonden erlaubt - mit Tiefenbeschränkung",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "3",
                            "desc": "Erdwärmesonden erlaubt - mit Auflagen",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "4",
                            "desc": "Erdwärmesonden gem. BAFU-Richtlinie unzulässig (Erstbeurteilung)",
                            "target_harmonized_value": 3,
                        },
                    ],
                }
            ],
        },
        "AR": {
            "active": True,
            "name": "AR",
            "ground_control_point": [
                [2755488, 1249846, 1, "zulässig (siehe Erläuterungen)"],
                [2756050, 1251316, 2, "bedingt zulässig (siehe Erläuterungen)"],
                [2755962, 1251037, 3, "nicht zulässig (siehe Erläuterungen)"],
            ],
            "wms_url": "https://www.geoportal.ch/services/wms/ktar",
            "query_url": "https://www.geoportal.ch/services/wms/ktar",
            "legend_url": "",
            "thematic_geoportal_url": "https://www.geoportal.ch/ktar/map/29?y=2728824.00&x=1243710.00&scale=100000&rotation=0",
            "info_format": "application/json",
            "style": "",
            "layers": [
                {
                    "name": "ch.geoportal.ver_entsorgung_kommunikation.29.0.erdwaermesonden_kt",
                    "property_name": "Info",
                    "property_values": [
                        {
                            "name": "zulässig (siehe Erläuterungen)",
                            "target_harmonized_value": 1,
                        },
                        {"name": "zulässig", "target_harmonized_value": 1},
                        {
                            "name": "bedingt zulässig (siehe Erläuterungen)",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "bedingt zulässig aufgrund: Hydrogeologie",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "bedingt zulässig aufgrund: Hydrogeologie, problematische Bohrung",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "nicht zulässig (siehe Erläuterungen)",
                            "target_harmonized_value": 3,
                        },
                        {"name": "unzulässig", "target_harmonized_value": 3},
                    ],
                }
            ],
        },
        "AI": {
            "active": True,
            "name": "AI",
            "ground_control_point": [
                [2751274, 1244545, 1, "zulässig (siehe Erläuterungen)"],
                [2747293, 1243755, 2, "bedingt zulässig (siehe Erläuterungen)"],
                [2748348, 1237931, 3, "nicht zulässig (siehe Erläuterungen)"],
            ],
            "wms_url": "https://www.geoportal.ch/services/wms/ktai",
            "query_url": "https://www.geoportal.ch/services/wms/ktai",
            "legend_url": "",
            "thematic_geoportal_url": "https://www.geoportal.ch/ktai/map/29?y=2728824.00&x=1243710.00&scale=100000&rotation=0",
            "info_format": "application/json",
            "style": "",
            "layers": [
                {
                    "name": "ch.geoportal.ver_entsorgung_kommunikation.29.0.erdwaermesonden_kt",
                    "property_name": "Info",
                    "property_values": [
                        {
                            "name": "zulässig (siehe Erläuterungen)",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "bedingt zulässig (siehe Erläuterungen)",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "nicht zulässig (siehe Erläuterungen)",
                            "target_harmonized_value": 3,
                        },
                    ],
                }
            ],
        },
        "AG": {
            "active": True,
            "name": "AG",
            "ground_control_point": [
                [2655805, 1258983, 2, "3"],
                [2653716, 1269536, 3, "6"],
                [2657482, 1264764, 2, "2"],
                [2658947, 1259532, 3, "4"],
                [2658947, 1240238, 1, "1"],
            ],
            "wms_url": "https://www.ag.ch/geoportal/services/afu_erdwaerme/MapServer/WMSServer",
            "query_url": "https://www.ag.ch/geoportal/services/afu_erdwaerme/MapServer/WMSServer",
            "legend_url": "",
            "thematic_geoportal_url": "https://www.ag.ch/geoportal/apps/onlinekarten/?basemap=base_landeskarten_sw::topicmaps.geo.ag.ch,1,true&center=2652503.58,1250363.05&z=3&layers=afu_erdwaerme::topicmaps.geo.ag.ch;1;true",
            "info_format": "application/geo+json",
            "style": "",
            "layers": [
                {
                    "name": "Eignung_Erdwärmenutzung55223",
                    "property_name": "G_Nutz_N",
                    "property_values": [
                        {
                            "name": "1",
                            "desc": "EWS möglich",
                            "target_harmonized_value": 1,
                        },
                        {
                            "name": "2",
                            "desc": "EWS mit geologischer Begleitung möglich",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "3",
                            "desc": "EWS mit geologischem Gutachten und geologischer Begleitung möglich",
                            "target_harmonized_value": 2,
                        },
                        {
                            "name": "4",
                            "desc": "Nur Grundwasserwärmepumpe möglich",
                            "target_harmonized_value": 3,
                        },
                        {
                            "name": "6",
                            "desc": "Keine Erdwärmenutzung möglich",
                            "target_harmonized_value": 3,
                        },
                    ],
                }
            ],
        },
    }
}
