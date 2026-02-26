"""
Script pour demander a Gemini de l'aide sur le design de Stock Advisor.
Utilise Playwright avec le profil Chrome existant.
"""
import asyncio
from playwright.async_api import async_playwright
import os

# Le prompt a envoyer a Gemini
PROMPT = """Je developpe une application Streamlit appelee "Stock Advisor" - un dashboard financier pour suivre les investissements en bourse.

Voici ce que j'ai actuellement:
- Theme sombre avec degrades violets (#6366f1 a #a855f7)
- Sidebar avec navigation par boutons
- Cards pour les metriques avec effets hover
- Design moderne type SaaS

J'ai besoin que tu me generes du CSS Streamlit moderne et creatif pour la page "Dashboard" qui affiche:
1. Un header avec le titre et un resume du portefeuille
2. 4 metriques principales (Valeur totale, Performance, Dividendes, Score)
3. Un graphique de performance
4. Une liste des top actions

Genere-moi le code CSS complet avec des styles modernes:
- Glassmorphism effects
- Gradients subtils
- Animations hover fluides
- Cards avec ombres et borders arrondis
- Design coherent dark mode

Donne-moi le code CSS pour st.markdown() dans Streamlit, pret a copier-coller. Format: st.markdown(STYLE_CSS, unsafe_allow_html=True)
"""

async def ask_gemini():
    # Chemin du profil Chrome de l'utilisateur
    user_data_dir = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data"

    async with async_playwright() as p:
        print("[INFO] Lancement de Chrome avec ton profil...")

        # Utiliser le profil Chrome existant (deja connecte a Google)
        try:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir,
                channel="chrome",
                headless=False,
                args=["--profile-directory=Default"]
            )
        except Exception as e:
            print(f"[ERREUR] Impossible d'utiliser Chrome: {e}")
            print("[INFO] Ferme Chrome si ouvert, puis relance ce script.")
            return

        page = browser.pages[0] if browser.pages else await browser.new_page()

        print("[INFO] Ouverture de Gemini...")
        await page.goto("https://gemini.google.com/app")

        # Attendre que la page charge completement
        print("[INFO] Attente du chargement (10 sec)...")
        await page.wait_for_timeout(10000)

        # Prendre un screenshot pour voir l'etat
        await page.screenshot(path="gemini_state.png")
        print("[INFO] Screenshot sauvegarde: gemini_state.png")

        try:
            # Chercher le champ de saisie avec plusieurs selecteurs possibles
            selectors = [
                'div[contenteditable="true"]',
                'rich-textarea div[contenteditable="true"]',
                '.ql-editor',
                'textarea',
                '[aria-label*="prompt"]',
                '[aria-label*="message"]'
            ]

            textarea = None
            for selector in selectors:
                try:
                    textarea = await page.wait_for_selector(selector, timeout=5000)
                    if textarea:
                        print(f"[OK] Champ trouve avec: {selector}")
                        break
                except:
                    continue

            if textarea:
                print("[INFO] Envoi du prompt...")
                await textarea.click()
                await page.wait_for_timeout(500)

                # Taper le texte caractere par caractere
                await page.keyboard.type(PROMPT, delay=10)
                await page.wait_for_timeout(2000)

                # Screenshot avant envoi
                await page.screenshot(path="gemini_before_send.png")

                # Envoyer avec Enter ou le bouton
                await page.keyboard.press("Enter")
                print("[OK] Prompt envoye!")

                # Attendre la reponse
                print("[INFO] Attente de la reponse (90 sec)...")
                await page.wait_for_timeout(90000)

                # Screenshot de la reponse
                await page.screenshot(path="gemini_response.png", full_page=True)
                print("[OK] Reponse capturee dans: gemini_response.png")

                # Essayer d'extraire le texte de la reponse
                response_elements = await page.query_selector_all('.response-content, .model-response, .message-content')
                for elem in response_elements:
                    text = await elem.inner_text()
                    if text and len(text) > 100:
                        # Sauvegarder dans un fichier
                        with open("gemini_css_response.txt", "w", encoding="utf-8") as f:
                            f.write(text)
                        print("[OK] Reponse sauvegardee dans: gemini_css_response.txt")
                        break

            else:
                print("[ERREUR] Champ de saisie non trouve.")
                print("[INFO] Es-tu connecte a Google dans Chrome?")
                await page.screenshot(path="gemini_error.png")

        except Exception as e:
            print(f"[ERREUR] {e}")
            await page.screenshot(path="gemini_error.png")

        print("\n" + "="*50)
        print("Regarde le navigateur pour voir la reponse de Gemini")
        print("Les screenshots sont sauvegardes dans le dossier courant")
        print("="*50)

        # Garder le navigateur ouvert 2 minutes pour que l'utilisateur puisse voir
        print("\n[INFO] Le navigateur reste ouvert 2 minutes...")
        await page.wait_for_timeout(120000)

        await browser.close()
        print("[INFO] Navigateur ferme.")

if __name__ == "__main__":
    print("="*50)
    print("Stock Advisor - Demande de design a Gemini")
    print("="*50)
    print("")
    print("IMPORTANT: Ferme Chrome avant de lancer ce script!")
    print("")
    asyncio.run(ask_gemini())
