from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

NB_UTILISATEURS = 12
MDP_PAR_DEFAUT = "Memoire2026!"


class Command(BaseCommand):
    help = "Crée le compte admin + 12 comptes étudiants de démarrage."

    def handle(self, *args, **options):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "Admin2026!")
            self.stdout.write(self.style.SUCCESS("Compte admin créé (admin / Admin2026!)"))
        else:
            self.stdout.write("Compte admin déjà existant.")

        for i in range(1, NB_UTILISATEURS + 1):
            uname = f"etudiant{i:02d}"
            if not User.objects.filter(username=uname).exists():
                User.objects.create_user(uname, f"{uname}@example.com", MDP_PAR_DEFAUT,
                                          first_name=f"Étudiant {i:02d}")
                self.stdout.write(f"Créé : {uname}")
            else:
                self.stdout.write(f"Déjà existant : {uname}")

        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé. {NB_UTILISATEURS} comptes étudiants (mot de passe: {MDP_PAR_DEFAUT}) + 1 admin (Admin2026!)."
        ))
