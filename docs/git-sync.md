# Synchroniser une branche locale avec sa branche distante

Ce guide explique comment récupérer les dernières modifications disponibles sur `origin` tout en conservant les changements présents dans votre copie locale. Il s'applique lorsque la commande `git push` est refusée avec l'erreur *non-fast-forward* parce que votre branche locale est en retard sur la branche distante.

## 1. Vérifier l'état courant

```bash
git status -sb
```

Cette commande résume l'état de votre branche. Si vous voyez des lignes comme `M app.py` ou `?? frontend/`, cela signifie que vous avez des modifications locales non enregistrées.

## 2. Sauvegarder provisoirement vos modifications locales

Si vous avez des fichiers modifiés ou non suivis, mettez-les de côté pour effectuer la mise à jour en toute sécurité. Utilisez `git stash` avec `-u` pour inclure aussi les fichiers non suivis :

```bash
git stash push -u -m "Sauvegarde avant synchronisation"
```

Vous pouvez vérifier que la zone de travail est propre en relançant `git status -sb`.

> 💡 *Alternative :* si vos changements sont prêts, vous pouvez les valider (`git commit`) au lieu de les stocker dans un stash.

## 3. Récupérer les changements distants

Rapatriez ensuite les derniers commits de la branche distante. Deux options s'offrent à vous :

### Option A : Rebaser la branche locale

```bash
git fetch origin
git rebase origin/fix/revert-62
```

Cette approche rejoue vos commits locaux au-dessus de la branche distante pour conserver un historique linéaire.

### Option B : Fusionner les changements distants

```bash
git pull origin fix/revert-62
```

Cette option créera un commit de fusion si des commits locaux existent déjà.

## 4. Réappliquer vos modifications locales

Si vous aviez utilisé `git stash`, récupérez vos fichiers :

```bash
git stash pop
```

Résoudre éventuellement les conflits, puis valider ou re-stasher si nécessaire.

## 5. Publier vos changements

Une fois votre branche locale synchronisée avec `origin/fix/revert-62` et vos modifications validées, vous pouvez pousser :

```bash
git push origin fix/revert-62
```

Si le push réussit, votre branche locale et distante sont désormais alignées.

## 6. Nettoyer les stashes inutiles

Si vous n'avez plus besoin de la sauvegarde, supprimez-la :

```bash
git stash drop
```

Vous pouvez lister les stashes disponibles via `git stash list` avant de les effacer.

---

### Questions fréquentes

- **Pourquoi `git push` refuse-t-il l'opération ?** Parce que la branche distante contient des commits que votre branche locale n'a pas encore.
- **Puis-je utiliser `git pull --rebase` directement ?** Oui, `git pull --rebase origin fix/revert-62` combine les étapes 3A et 4, mais assurez-vous d'avoir sauvegardé vos modifications non committées avant.
- **Que faire en cas de conflits ?** Modifiez les fichiers concernés, validez les changements (`git add`), puis poursuivez le `rebase` (`git rebase --continue`) ou finalisez la fusion (`git commit`).
