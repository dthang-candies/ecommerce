import os
import sys
import webbrowser
import threading
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

# Presentation Layer Components
class SearchResultView:
    """
    Presentation Layer: Search Result View
    Responsible for rendering search results, product details, and orders.
    """

    @staticmethod
    def render_products(title: str, results: List[Tuple[Dict[str, Any], float]]) -> None:
        print(f"\n--- {title} ---")
        if not results:
            print("No matching products found.")
            return

        for idx, (product, score) in enumerate(results, start=1):
            name = product.get("name", "Unknown")
            cat = product.get("category", "")
            color = product.get("color", "")
            price = product.get("price", 0)
            stock = product.get("stock", 0)
            print(f"{idx}. {name} | Category: {cat} | Color: {color} | Price: ${price} | Stock: {stock} | Score: {score}")

    @staticmethod
    def render_order(order: Optional[Dict[str, Any]], order_id: str) -> None:
        print(f"\n--- Order Search Result for: {order_id} ---")
        if not order:
            print(f"Order '{order_id}' was not found in the system.")
            return

        print(f"Order ID   : {order.get('order_id')}")
        print(f"Customer ID: {order.get('customer_id')}")
        print(f"Date       : {order.get('date', 'N/A')}")
        print(f"Status     : {order.get('status')}")
        print(f"Total      : ${order.get('total')}")
        if "items" in order and order["items"]:
            print("Items      :")
            for it in order["items"]:
                print(f"  - Product #{it.get('product_id')} x {it.get('quantity')} @ ${it.get('price')}")


class VoiceInput:
    """
    Presentation Layer: Voice Input component.
    Captures voice input (or simulated audio string) and delegates to SpeechService.
    """
    @staticmethod
    def capture_voice(simulated_audio: str) -> str:
        return simulated_audio.strip()


class ImageUpload:
    """
    Presentation Layer: Image Upload component.
    Handles image uploads / feature representations.
    """
    @staticmethod
    def upload_image(image_path_or_vector: Any) -> Any:
        return image_path_or_vector


class SearchUI:
    """
    Presentation Layer: Search UI
    Connects user interactions to Application Layer services.
    Enforces separation: UI -> Application -> Data (No direct access to repositories).
    """

    def __init__(
        self,
        search_service,
        query_service,
        speech_service=None,
        ranking_service=None,
        image_service=None
    ):
        self.search_service = search_service
        self.query_service = query_service
        self.speech_service = speech_service
        self.ranking_service = ranking_service
        self.image_service = image_service
        self.view = SearchResultView()
        self.voice_input = VoiceInput()
        self.image_upload = ImageUpload()

    def search_by_text(self, text: str, apply_ranking: bool = False) -> List[Tuple[Dict[str, Any], float]]:
        """1. Text Search Mode: UI -> QueryService -> SearchService -> RankingService"""
        query = self.query_service.text_query(text)
        candidates = self.search_service.search_text(query["query"])

        if apply_ranking and self.ranking_service:
            results = self.ranking_service.rank(candidates)
        else:
            results = candidates
        return results

    def search_by_voice(self, audio_input: str, apply_ranking: bool = False) -> List[Tuple[Dict[str, Any], float]]:
        """
        2. Voice Search Mode (simulated sequence from UML spec):
        Customer -> SearchUI -> SpeechService -> QueryService -> SearchService -> RankingService
        """
        raw_audio = self.voice_input.capture_voice(audio_input)
        if self.speech_service:
            transcribed_text = self.speech_service.transcribe(raw_audio)
        else:
            transcribed_text = raw_audio

        query = self.query_service.voice_query(transcribed_text)
        candidates = self.search_service.search_text(query["query"])

        if apply_ranking and self.ranking_service:
            results = self.ranking_service.rank(candidates)
        else:
            results = candidates
        return results

    def search_by_image(self, image_input: Any, apply_ranking: bool = False) -> List[Tuple[Dict[str, Any], float]]:
        """3. Image Search Mode: UI -> ImageService -> QueryService -> SearchService"""
        uploaded = self.image_upload.upload_image(image_input)
        if self.image_service:
            embedding = self.image_service.encode_image(uploaded)
        else:
            embedding = uploaded

        query = self.query_service.image_query(embedding)
        candidates = self.search_service.search_image(query["embedding"])

        if apply_ranking and self.ranking_service:
            results = self.ranking_service.rank(candidates)
        else:
            results = candidates
        return results

    def search_multimodal(
        self,
        text: Optional[str] = None,
        image_input: Optional[Any] = None,
        lambda_t: float = 0.5,
        lambda_i: float = 0.5,
        apply_ranking: bool = False
    ) -> List[Tuple[Dict[str, Any], float]]:
        """4. Multimodal Search Mode: Combined text + image query"""
        embedding = None
        if image_input is not None:
            uploaded = self.image_upload.upload_image(image_input)
            if self.image_service:
                embedding = self.image_service.encode_image(uploaded)
            else:
                embedding = uploaded

        query = self.query_service.multimodal_query(
            text=text,
            embedding=embedding,
            weights={"text": lambda_t, "image": lambda_i}
        )

        candidates = self.search_service.search_multimodal(
            query_text=query["query"],
            query_embedding=query["embedding"],
            lambda_t=lambda_t,
            lambda_i=lambda_i
        )

        if apply_ranking and self.ranking_service:
            results = self.ranking_service.rank(candidates)
        else:
            results = candidates
        return results

    def search_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """5. Order Search Mode"""
        query = self.query_service.order_query(order_id)
        return self.search_service.search_order(query["order_id"])

    def interactive_cli(self) -> None:
        """Interactive console CLI interface."""
        while True:
            print("\n" + "="*50)
            print("  MULTIMODAL E-COMMERCE SEARCH - CONSOLE UI")
            print("="*50)
            print("1. Text Search (e.g., 'black running shoes')")
            print("2. Simulated Voice Search (e.g., 'find black shoes')")
            print("3. Image Search (e.g., category 'shoes' or vector)")
            print("4. Multimodal Search (Text + Image)")
            print("5. Order Search (e.g., 'O001')")
            print("6. Exit")
            choice = input("\nSelect an option (1-6): ").strip()

            if choice == "1":
                q = input("Enter text query: ").strip()
                res = self.search_by_text(q)
                self.view.render_products(f"Text Search: '{q}'", res)
            elif choice == "2":
                q = input("Speak (type simulated audio): ").strip()
                res = self.search_by_voice(q)
                self.view.render_products(f"Voice Search: '{q}'", res)
            elif choice == "3":
                q = input("Enter image prototype (shoes / bag / clothing / watch): ").strip()
                res = self.search_by_image(q)
                self.view.render_products(f"Image Search: '{q}'", res)
            elif choice == "4":
                t = input("Enter text query: ").strip()
                img = input("Enter image prototype (shoes / bag / clothing): ").strip()
                res = self.search_multimodal(text=t, image_input=img)
                self.view.render_products(f"Multimodal Search ('{t}' + '{img}')", res)
            elif choice == "5":
                oid = input("Enter order ID (e.g., O001, O002, 20261001): ").strip()
                ord_res = self.search_order(oid)
                self.view.render_order(ord_res, oid)
            elif choice == "6":
                print("Exiting search system.")
                break
            else:
                print("Invalid selection. Please choose 1-6.")


def create_flask_app(search_ui: SearchUI):
    """
    Creates and configures the Flask Web Application providing
    the full modern interactive GUI for browser use.
    """
    from flask import Flask, render_template, request, jsonify, send_from_directory

    base_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static")
    )

    project_root = os.path.dirname(base_dir)
    images_dir = os.path.join(project_root, "data", "images")

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/images/<path:filename>")
    def serve_image(filename):
        return send_from_directory(images_dir, filename)

    @app.route("/api/products", methods=["GET"])
    def get_products():
        prods = search_ui.search_service.repository.all_products()
        return jsonify({"products": prods})

    @app.route("/api/product/<product_id>", methods=["GET"])
    def get_product(product_id):
        prod = search_ui.search_service.repository.find_by_id(product_id)
        return jsonify({"product": prod})

    @app.route("/api/search/text", methods=["POST"])
    def api_search_text():
        data = request.get_json() or {}
        q = data.get("query", "")
        apply_ranking = data.get("apply_ranking", False)
        raw_res = search_ui.search_by_text(q, apply_ranking=apply_ranking)
        formatted = [{"product": p, "score": s} for p, s in raw_res]
        return jsonify({
            "mode_title": f"Text Search: '{q}'",
            "results": formatted
        })

    @app.route("/api/search/voice", methods=["POST"])
    def api_search_voice():
        data = request.get_json() or {}
        audio_text = data.get("audio_text", "")
        apply_ranking = data.get("apply_ranking", False)
        raw_res = search_ui.search_by_voice(audio_text, apply_ranking=apply_ranking)
        formatted = [{"product": p, "score": s} for p, s in raw_res]
        return jsonify({
            "mode_title": f"Voice Search: '{audio_text}'",
            "results": formatted
        })

    @app.route("/api/search/image", methods=["POST"])
    def api_search_image():
        data = request.get_json() or {}
        embedding = data.get("embedding")
        apply_ranking = data.get("apply_ranking", False)
        raw_res = search_ui.search_by_image(embedding, apply_ranking=apply_ranking)
        formatted = [{"product": p, "score": s} for p, s in raw_res]
        return jsonify({
            "mode_title": "Visual Similarity Search",
            "results": formatted
        })

    @app.route("/api/search/multimodal", methods=["POST"])
    def api_search_multimodal():
        data = request.get_json() or {}
        text = data.get("text", "")
        embedding = data.get("embedding")
        lambda_t = float(data.get("lambda_t", 0.5))
        lambda_i = float(data.get("lambda_i", 0.5))
        apply_ranking = data.get("apply_ranking", False)
        raw_res = search_ui.search_multimodal(
            text=text,
            image_input=embedding,
            lambda_t=lambda_t,
            lambda_i=lambda_i,
            apply_ranking=apply_ranking
        )
        formatted = [{"product": p, "score": s} for p, s in raw_res]
        return jsonify({
            "mode_title": f"Multimodal Search Fusion (Text + Image)",
            "results": formatted
        })

    @app.route("/api/orders", methods=["GET"])
    def get_all_orders():
        if search_ui.search_service.order_repository:
            orders = search_ui.search_service.order_repository.all_orders()
        else:
            orders = []
        return jsonify({"orders": orders})

    @app.route("/api/order/<order_id>", methods=["GET"])
    def get_order(order_id):
        order = search_ui.search_order(order_id)
        return jsonify({"order": order})

    @app.route("/api/evaluation", methods=["GET"])
    def get_evaluation():
        all_ords = search_ui.search_service.order_repository.all_orders() if search_ui.search_service.order_repository else []
        target_ord_id = all_ords[0]["order_id"] if all_ords else "O001"
        test_set = [
            {"query": "black shoes", "mode": "Text", "expected_keyword": "Shoes", "run": lambda: search_ui.search_by_text("black shoes")},
            {"query": "running shoes", "mode": "Voice", "expected_keyword": "Shoes", "run": lambda: search_ui.search_by_voice("running shoes")},
            {"query": "shoe image [0.9, 0.1, 0.2]", "mode": "Image", "expected_keyword": "Shoes", "run": lambda: search_ui.search_by_image([0.9, 0.1, 0.2])},
            {"query": f"order {target_ord_id}", "mode": "Order", "expected_id": target_ord_id, "run": lambda: [({"name": f"Order {target_ord_id}", "id": target_ord_id}, 1.0)] if search_ui.search_order(target_ord_id) else []},
        ]
        results = []
        successful = 0
        for item in test_set:
            res = item["run"]()
            top1 = res[0][0]["name"] if res else "None"
            top1_cat = res[0][0].get("category", "") if res else ""
            score = res[0][1] if res else 0.0
            is_success = False
            if res:
                if "expected_keyword" in item:
                    kw = item["expected_keyword"].lower()
                    if kw in top1.lower() or kw in top1_cat.lower() or (kw == "shoes" and "giày" in top1.lower()):
                        is_success = True
                elif "expected_id" in item and (item["expected_id"] in top1 or item["expected_id"] == top1):
                    is_success = True
            if is_success:
                successful += 1
            results.append({
                "query": item["query"],
                "mode": item["mode"],
                "top1_result": top1,
                "score": score,
                "success": is_success
            })


        total = len(test_set)
        rate = round((successful / total) * 100, 1)
        return jsonify({
            "evaluation": results,
            "total": total,
            "successful": successful,
            "success_rate": rate
        })

    @app.route("/api/db/status", methods=["GET"])
    def get_db_status():
        from data.db_connection import test_connection, get_driver_name
        from data.db_config import get_db_config
        is_ok, msg, details = test_connection()
        repo = getattr(search_ui.search_service, "repository", None)
        source = getattr(repo, "data_source", "unknown")
        cfg = get_db_config()
        return jsonify({
            "connected": is_ok,
            "message": msg,
            "data_source": source,
            "driver": get_driver_name(),
            "database": cfg.get("database"),
            "host": cfg.get("host"),
            "port": cfg.get("port")
        })

    return app



def start_web_ui(search_ui: SearchUI, port: int = 5050, open_browser: bool = True):
    """Starts the Flask interactive web application and opens default browser."""
    app = create_flask_app(search_ui)
    url = f"http://127.0.0.1:{port}"
    print("\n" + "="*60)
    print(f"🚀 Multimodal Search Interactive Web UI is running at:")
    print(f"👉 {url}")
    print("="*60)

    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    # Run Flask server
    app.run(host="127.0.0.1", port=port, debug=False)
