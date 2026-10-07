import sys
import numpy as np

# Layer 3: Data Layer
from data.product_repository import ProductRepository
from data.order_repository import OrderRepository
from data.vector_index import VectorIndex

# Layer 2: Application / Intelligence Layer
from application.query_service import QueryService
from application.search_service import SearchService
from application.speech_service import SpeechService
from application.image_service import ImageService
from application.ranking_service import RankingService

# Layer 1: Presentation Layer
from presentation.search_ui import SearchUI, start_web_ui
from presentation.desktop_gui import start_desktop_gui


def init_system() -> SearchUI:
    """Initializes and wires the three layers together."""
    # Data Layer
    product_repo = ProductRepository()
    order_repo = OrderRepository()
    vector_index = VectorIndex()
    vector_index.load_from_repository(product_repo)

    # Application / Intelligence Layer
    query_service = QueryService()
    speech_service = SpeechService()
    image_service = ImageService()
    ranking_service = RankingService(alpha=0.6, beta=0.3, gamma=0.1)

    search_service = SearchService(
        repository=product_repo,
        vector_index=vector_index,
        order_repository=order_repo,
        ranking_service=ranking_service
    )

    # Presentation Layer
    ui = SearchUI(
        search_service=search_service,
        query_service=query_service,
        speech_service=speech_service,
        ranking_service=ranking_service,
        image_service=image_service
    )

    return ui


def run_automated_demo():
    print("==================================================")
    print("=== Multimodal E-Commerce Search Demo (Assignment 05/06) ===")
    print("==================================================")

    ui = init_system()
    query_service = ui.query_service
    search_service = ui.search_service
    speech_service = ui.speech_service
    ranking_service = ui.ranking_service

    # Mode 1: Text Search
    print("\n--------------------------------------------------")
    print("Mode 1: Text Search")
    print("Input: 'black shoes'")
    query = query_service.text_query("black shoes")
    print(f"Query Representation: {query}")
    results = search_service.search_text(query["query"])
    print("Results:")
    for product, score in results[:3]:
        print(f"  {product['name']} | score = {score}")

    # Mode 2: Voice Search
    print("\n--------------------------------------------------")
    print("Mode 2: Voice Search (Simulated Speech-to-Text)")
    audio = "find running shoes"
    print(f"Audio Input: '{audio}'")
    text = speech_service.transcribe(audio)
    print(f"Transcribed Text: '{text}'")
    query = query_service.voice_query(text)
    print(f"Query Representation: {query}")
    results = search_service.search_text(query["query"])
    print("Results:")
    for product, score in results[:3]:
        print(f"  {product['name']} | score = {score}")

    # Mode 3: Image Search
    print("\n--------------------------------------------------")
    print("Mode 3: Image-based Search (Cosine Vector Similarity)")
    query_vec = np.array([0.9, 0.1, 0.2])
    print(f"Image Feature Vector z_q: {query_vec.tolist()}")
    query = query_service.image_query(query_vec)
    image_results = search_service.search_image(query["embedding"], top_k=3)
    print("Results:")
    for product, score in image_results:
        print(f"  {product['name']} | similarity = {score}")

    # Mode 4: Multimodal Search
    print("\n--------------------------------------------------")
    print("Mode 4: Multimodal Search (Text + Image Fusion)")
    text_input = "running"
    img_embedding = np.array([0.9, 0.1, 0.2])
    print(f"Text Input: '{text_input}' | Image Embedding: {img_embedding.tolist()}")
    mm_query = query_service.multimodal_query(text=text_input, embedding=img_embedding, weights={"text": 0.5, "image": 0.5})
    mm_results = search_service.search_multimodal(
        query_text=mm_query["query"],
        query_embedding=mm_query["embedding"],
        lambda_t=0.5,
        lambda_i=0.5
    )
    print("Combined Retrieval Results:")
    for product, score in mm_results[:3]:
        print(f"  {product['name']} | combined score = {score}")

    print("\nApplying Multi-signal Ranking (with business stock & price signal):")
    ranked_mm = ranking_service.rank(mm_results[:5])
    for product, score in ranked_mm[:3]:
        print(f"  {product['name']} | final rank score = {score} (stock={product['stock']}, price=${product['price']})")

    # Mode 5: Order Search
    print("\n--------------------------------------------------")
    print("Mode 5: Order Search")
    all_ords = search_service.order_repository.all_orders() if search_service.order_repository else []
    sample_order_id = all_ords[0]["order_id"] if all_ords else "O001"
    print(f"Input Order ID: '{sample_order_id}'")
    order = search_service.search_order(sample_order_id)
    if order:
        print(f"Order: {order['order_id']}")
        print(f"Status: {order['status']}")
        print(f"Total: ${order['total']}")

    # Evaluation Suite (Section 22, Table 3)
    print("\n--------------------------------------------------")
    print("Experimental Evaluation (Section 22, Table 3):")
    target_ord_id = sample_order_id
    test_set = [
        {"query": "black shoes", "mode": "Text", "expected_keyword": "Shoes", "run": lambda: search_service.search_text("black shoes")},
        {"query": "running shoes", "mode": "Voice", "expected_keyword": "Shoes", "run": lambda: search_service.search_text(speech_service.transcribe("running shoes"))},
        {"query": "shoe image [0.9, 0.1, 0.2]", "mode": "Image", "expected_keyword": "Shoes", "run": lambda: search_service.search_image(np.array([0.9, 0.1, 0.2]))},
        {"query": f"order {target_ord_id}", "mode": "Order", "expected_id": target_ord_id, "run": lambda: [({"name": f"Order {target_ord_id}", "id": target_ord_id}, 1.0)] if search_service.search_order(target_ord_id) else []},
    ]

    successful = 0
    total = len(test_set)
    print(f"{'Query':<28} | {'Mode':<8} | {'Top-1 Result':<25} | {'Success'}")
    print("-" * 75)

    for item in test_set:
        res = item["run"]()
        top1_name = res[0][0]["name"] if res else "None"
        top1_cat = res[0][0].get("category", "") if res else ""
        is_success = False
        if res:
            if "expected_keyword" in item:
                kw = item["expected_keyword"].lower()
                if kw in top1_name.lower() or kw in top1_cat.lower() or (kw == "shoes" and "giày" in top1_name.lower()):
                    is_success = True
            elif "expected_id" in item and (item["expected_id"] in top1_name or item["expected_id"] == top1_name):
                is_success = True

        if is_success:
            successful += 1
        print(f"{item['query']:<28} | {item['mode']:<8} | {top1_name:<25} | {'Yes' if is_success else 'No'}")

    success_rate = (successful / total) * 100
    print("-" * 75)
    print(f"Total Queries: {total} | Successful: {successful} | Success Rate: {success_rate:.1f}%\n")



def main():
    ui = init_system()

    if "--demo" in sys.argv:
        # Run automated console demo
        run_automated_demo()
    elif "--cli" in sys.argv:
        # Run console interactive menu
        ui.interactive_cli()
    elif "--gui" in sys.argv:
        # Run native desktop Tkinter GUI
        print("Launching native Desktop GUI...")
        start_desktop_gui(ui)
    else:
        # Default: Launch rich Interactive Web UI in browser
        port = 5050
        print("\nStarting Interactive Web Interface...")
        start_web_ui(ui, port=port, open_browser=True)


if __name__ == "__main__":
    main()
