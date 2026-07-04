// Fait défiler le questionnaire un traitement à la fois : chaque page
// contient 10 <div class="traitement-card" data-traitement="a"..."j">
// empilées dans le <form> (toutes soumises ensemble, une seule ne change
// que la visibilité). Navigation via les pastilles a→j ou les boutons
// .traitement-precedent/.traitement-suivant présents dans chaque carte.
document.addEventListener("DOMContentLoaded", function () {
  var cartes = Array.from(document.querySelectorAll(".traitement-card"));
  var pastilles = Array.from(document.querySelectorAll(".traitement-pastille"));
  if (cartes.length === 0) {
    return;
  }

  var indexActif = 0;

  function afficher(index) {
    if (index < 0 || index >= cartes.length) {
      return;
    }
    indexActif = index;
    cartes.forEach(function (carte, i) {
      carte.classList.toggle("hidden", i !== index);
    });
    pastilles.forEach(function (pastille, i) {
      pastille.classList.toggle("bg-blue-600", i === index);
      pastille.classList.toggle("text-white", i === index);
      pastille.classList.toggle("bg-gray-100", i !== index);
      pastille.classList.toggle("text-gray-700", i !== index);
    });
    cartes[index].scrollIntoView({ behavior: "smooth", block: "start" });
  }

  pastilles.forEach(function (pastille, i) {
    pastille.addEventListener("click", function () {
      afficher(i);
    });
  });
  document.querySelectorAll(".traitement-suivant").forEach(function (bouton) {
    bouton.addEventListener("click", function () {
      afficher(indexActif + 1);
    });
  });
  document.querySelectorAll(".traitement-precedent").forEach(function (bouton) {
    bouton.addEventListener("click", function () {
      afficher(indexActif - 1);
    });
  });

  // Rouvre directement sur la première carte en erreur après une soumission invalide.
  var indexErreur = cartes.findIndex(function (carte) {
    return carte.querySelector(".erreurs-traitement");
  });
  afficher(indexErreur >= 0 ? indexErreur : 0);
});
