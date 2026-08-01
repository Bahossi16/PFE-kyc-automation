-- =======================================================
-- Script d'initialisation de la base de données CBS (Core Banking System)
-- Contexte : Tunisie (Simulation KYC sur Images Réelles)
-- Mis à jour : Ajout des vrais profils de test (Factures STEG nouv_f)
-- =======================================================

CREATE DATABASE IF NOT EXISTS cbs_kyc CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cbs_kyc;

-- 1. Table des Clients (Données de référence CBS)
DROP TABLE IF EXISTS kyc_logs;
DROP TABLE IF EXISTS clients;
CREATE TABLE clients (
    client_id VARCHAR(10) PRIMARY KEY,
    cin VARCHAR(8) NOT NULL UNIQUE,
    nom VARCHAR(50) NOT NULL,
    prenom VARCHAR(50) NOT NULL,
    nom_ar VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    prenom_ar VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    adresse VARCHAR(150) NOT NULL,
    email VARCHAR(100) NOT NULL,
    salaire DECIMAL(10,3) DEFAULT NULL,
    pays VARCHAR(30) DEFAULT 'Tunisie',
    date_creation DATE NOT NULL,
    date_derniere_revue DATE NOT NULL,
    date_prochaine_revue DATE NOT NULL,
    niveau_risque VARCHAR(20) DEFAULT 'Faible',
    statut_kyc VARCHAR(30) DEFAULT 'Normal'
);

-- =======================================================
-- CLIENTS DE TEST (Extraits des vraies factures STEG nouv_f)
-- Ces données CBS simulent ce que la banque connaît déjà.
-- L'adresse CBS utilise l'orthographe OFFICIELLE du référentiel UIB.
-- =======================================================

INSERT INTO clients (client_id, cin, nom, prenom, nom_ar, prenom_ar, adresse, email, salaire, date_creation, date_derniere_revue, date_prochaine_revue, niveau_risque, statut_kyc) VALUES

-- -------------------------------------------------------
-- Profil 1 : Correspond à la facture STEG ref 038715391
-- Nom OCR attendu : MR BMASSAOUD FATMA  -> Jaro-Winkler ~98%
-- Adresse CBS : orthographe officielle UIB (JBEL JLOUD 1009)
-- Test attendu : Nom CONFORME, Adresse DIVERGENCE (adresse longue vs courte)
-- -------------------------------------------------------
('FC-2001', '12345678', 'MASSAOUD', 'FATMA', NULL, NULL,
 'JBEL JLOUD 1009',
 'fatma.massaoud@email.com', NULL,
 '2020-03-15', '2020-03-15', '2025-03-15', 'Faible', 'A Mettre a Jour'),

-- -------------------------------------------------------
-- Profil 2 : Correspond à la facture STEG ref 038715420
-- Nom OCR attendu : MR B MASSAOUD ABDALLAH -> Jaro-Winkler ~80%
-- Adresse CBS : orthographe officielle UIB (JBEL JLOUD 1046)
-- Test attendu : Adresse CONFORME après filtre phonétique
-- -------------------------------------------------------
('FC-2002', '87654321', 'MASSAOUD', 'ABDALLAH', NULL, NULL,
 'JBEL JLOUD 1046',
 'abdallah.massaoud@email.com', NULL,
 '2019-07-22', '2022-07-22', '2025-07-22', 'Moyen', 'A Mettre a Jour'),

-- -------------------------------------------------------
-- Profil 5 : Profil pour test Multi-Documents (CIN + Paie)
-- Nom : OMRANE MBARKI, CIN: 02240639
-- -------------------------------------------------------
('FC-3001', '02240639', 'MBARKI', 'OMRANE', NULL, NULL,
 'ADRESSE INCONNUE',
 'omrane.mbarki@email.com', 2000.000,
 '1990-01-01', '2020-01-01', '2030-01-01', 'Moyen', 'A Mettre a Jour'),

-- -------------------------------------------------------
-- Profil 3 : Correspond à la facture STEG ref 157748260
-- Nom OCR attendu : RES FLORIA -> Jaro-Winkler 100%
-- Adresse CBS : CITE LAGAZELLE
-- -------------------------------------------------------
('FC-2003', '55555555', 'FLORIA', '', NULL, NULL,
 'CITE LAGAZELLE',
 'syndic.floria@email.com', NULL,
 '2021-01-01', '2023-01-01', '2026-01-01', 'Faible', 'A Mettre a Jour'),

-- -------------------------------------------------------
-- Profil FC-1001 : CIN réelle testée avec OCR
-- Nom OCR: سويبقي / الاسم: دليلة
-- -------------------------------------------------------
('FC-1001', '12621583', 'SOUIBGUI', 'DALILA', 'سويبقي', 'دليلة',
 '12 RUE DE LA REPUBLIQUE, TUNIS 1000',
 'dalila.souibgui@email.com', NULL,
 '2019-06-12', '2019-06-12', '2026-06-12', 'Faible', 'A Mettre a Jour'),

-- -------------------------------------------------------
-- Profil FC-1002 : CIN réelle testée avec OCR
-- Nom OCR: بنعمار / الاسم: وصال
-- -------------------------------------------------------
('FC-1002', '13511348', 'BENNAMAR', 'WISAL', 'بنعمار', 'وصال',
 '42 AVENUE HABIB BOURGUIBA, SOUSSE 4000',
 'wisal.bennamar@email.com', NULL,
 '2018-05-10', '2024-05-10', '2025-05-10', 'Moyen', 'A Mettre a Jour'),

-- -------------------------------------------------------
-- Profil 4 : Client CONFORME (pour tester le cas "tout va bien")
-- -------------------------------------------------------
('FC-1003', '09988776', 'GHARBI', 'AMINE', NULL, NULL,
 'VILLA 5 ROUTE DE TENIOUR, SFAX 3012',
 'amine.gharbi@email.com', NULL,
 '2024-11-20', '2024-11-20', '2031-11-20', 'Faible', 'Normal'),

-- -------------------------------------------------------
-- Profil 5 : Client risque élevé, dossier expiré
-- -------------------------------------------------------
('FC-1004', '05566778', 'CHAABANE', 'SONIA', NULL, NULL,
 'CITE OLYMPIQUE, TUNIS 1003',
 'sonia.chaabane@email.com', NULL,
 '2017-01-10', '2020-01-10', '2021-01-10', 'Elevé', 'En Opposition');


-- 2. Table des Logs de Revue KYC (Historique des analyses)
CREATE TABLE kyc_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    client_id VARCHAR(10),
    date_revue DATETIME DEFAULT CURRENT_TIMESTAMP,
    document_analyse VARCHAR(100),
    statut_resultat VARCHAR(30),
    details_anomalies TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);
