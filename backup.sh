#!/bin/bash
# backup.sh

# Exécute pg_dump et le compresse, puis le stocke dans le volume de données du backup.
pg_dump -h db -U $POSTGRES_USER -d $POSTGRES_DB | gzip > /backups/epicerie_backup_$(date +\%Y\%m\%d_\%H\%M\%S).sql.gz
echo "Backup créé: epicerie_backup_$(date +\%Y\%m\%d_\%H\%M\%S).sql.gz"

# Optionnel: suppression des fichiers de plus de 7 jours
find /backups -type f -name "*.sql.gz" -mtime +7 -delete
echo "Nettoyage des anciens backups effectué."
