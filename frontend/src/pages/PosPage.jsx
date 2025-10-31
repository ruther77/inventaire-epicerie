import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { checkoutCart, fetchProducts } from '../api/client.js';

export default function PosPage() {
  const { data: products = [] } = useQuery({
    queryKey: ['products'],
    queryFn: fetchProducts,
  });

  const [selectedId, setSelectedId] = useState('');
  const [qty, setQty] = useState(1);
  const [cart, setCart] = useState([]);

  const mutation = useMutation({
    mutationFn: checkoutCart,
    onSuccess: (response) => {
      if (response.success) {
        setCart([]);
      }
    },
  });

  const selectedProduct = products.find((product) => String(product.id) === selectedId);

  const handleAdd = () => {
    if (!selectedProduct) {
      return;
    }
    setCart((previous) => [
      ...previous,
      {
        id: selectedProduct.id,
        nom: selectedProduct.nom,
        prix_vente: selectedProduct.prix_vente,
        tva: selectedProduct.tva ?? 0,
        qty,
      },
    ]);
    setQty(1);
  };

  const total = cart.reduce((sum, line) => sum + (line.prix_vente || 0) * line.qty, 0);

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Vente</p>
          <h1>Point de vente</h1>
          <p className="page-description">
            Encaissez rapidement tout en conservant vos préférences produits et paniers favoris.
          </p>
        </div>
      </header>
      <section className="card">
        <div className="grid two-columns">
          <div>
            <h2>Ajouter un article</h2>
            <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
              <option value="">Sélectionner un produit…</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.nom} ({product.prix_vente.toFixed(2)} €)
                </option>
              ))}
            </select>
            <input
              type="number"
              min="1"
              value={qty}
              onChange={(event) => setQty(Number(event.target.value) || 1)}
            />
            <button type="button" onClick={handleAdd} disabled={!selectedProduct}>
              Ajouter au panier
            </button>
          </div>
          <div>
            <h2>Panier</h2>
            {cart.length === 0 ? (
              <p>Le panier est vide.</p>
            ) : (
              <ul className="pos-cart-list">
                {cart.map((item, index) => (
                  <li key={`${item.id}-${index}`}>
                    <div>
                      <strong>{item.nom}</strong>
                      <span>× {item.qty}</span>
                    </div>
                    <span>{(item.prix_vente * item.qty).toFixed(2)} €</span>
                  </li>
                ))}
              </ul>
            )}
            <p className="pos-total">Total: {total.toFixed(2)} €</p>
            <button
              type="button"
              onClick={() => mutation.mutate({ cart, username: 'spa-user' })}
              disabled={cart.length === 0 || mutation.isLoading}
            >
              Finaliser la vente
            </button>
            {mutation.isLoading && <p>Validation de la vente…</p>}
            {mutation.data?.success && mutation.data.receipt_filename && (
              <p>
                Vente validée. Ticket: <code>{mutation.data.receipt_filename}</code>
              </p>
            )}
            {mutation.data && !mutation.data.success && <p>Erreur: {mutation.data.message}</p>}
          </div>
        </div>
      </section>
    </div>
  );
}
