const FAVORITES = [
  { id: 'fav-1', name: 'Fromage de chèvre', category: 'Frais' },
  { id: 'fav-2', name: 'Confiture fraise', category: 'Épicerie sucrée' },
];

export default function FavoritesPage() {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Compte</p>
          <h1>Favoris</h1>
          <p className="page-description">
            Epinglez vos produits préférés et retrouvez-les instantanément dans le catalogue.
          </p>
        </div>
        <div className="page-badges">
          <span className="badge badge-count">{FAVORITES.length}</span>
        </div>
      </header>
      <section className="card">
        <h2>Produits sauvegardés</h2>
        <ul className="favorites-list">
          {FAVORITES.map((item) => (
            <li key={item.id}>
              <span>{item.name}</span>
              <span className="favorite-category">{item.category}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
