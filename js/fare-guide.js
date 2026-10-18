const fareRoutes = {
  "lahug|colon": {
    labels: ["Lahug", "Colon"],
    fares: { jeepney: [13, 20], habal: [25, 40], taxi: [120, 200] },
  },
  "colon|sm-city": {
    labels: ["Colon", "SM City Cebu"],
    fares: { jeepney: [15, 15], habal: [35, 55], taxi: [90, 130] },
  },
  "parkmall|it-park": {
    labels: ["Parkmall", "IT Park"],
    fares: { jeepney: [15, 15], habal: [35, 55], taxi: [120, 180] },
  },
  "tabunok|south-terminal": {
    labels: ["Tabunok", "Cebu South Bus Terminal"],
    fares: { jeepney: [15, 20], habal: [45, 70], taxi: [180, 260] },
  },
  "basak|airport": {
    labels: ["Basak", "Mactan-Cebu International Airport"],
    fares: { jeepney: [20, 20], habal: [40, 65], taxi: [100, 160] },
  },
};

const fareForm = document.querySelector("#fare-form");
const fareFrom = document.querySelector("#fare-from");
const fareTo = document.querySelector("#fare-to");
const passengerType = document.querySelector("#passenger-type");
const fareError = document.querySelector("#fare-error");

function formatFareRange([minimum, maximum], discount) {
  const discountedMinimum = Math.round(minimum * discount);
  const discountedMaximum = Math.round(maximum * discount);
  return discountedMinimum === discountedMaximum
    ? `₱${discountedMinimum}`
    : `₱${discountedMinimum} - ₱${discountedMaximum}`;
}

function calculateFare() {
  const route = fareRoutes[`${fareFrom.value}|${fareTo.value}`];
  if (!route) {
    document.querySelector("#fare-total").textContent = "—";
    document.querySelector("#fare-route-label").textContent = "No sample fare available for this route";
    document.querySelector("#jeepney-fare").textContent = "—";
    document.querySelector("#habal-fare").textContent = "—";
    document.querySelector("#taxi-fare").textContent = "—";
    fareError.textContent = "No sample fare is available for this origin and destination. Choose a listed sample route.";
    fareError.classList.add("is-visible");
    return;
  }

  const discount = passengerType.value === "regular" ? 1 : 0.8;
  const fareRanges = {
    jeepney: formatFareRange(route.fares.jeepney, discount),
    habal: formatFareRange(route.fares.habal, discount),
    taxi: formatFareRange(route.fares.taxi, discount),
  };

  document.querySelector("#jeepney-fare").textContent = fareRanges.jeepney;
  document.querySelector("#habal-fare").textContent = fareRanges.habal;
  document.querySelector("#taxi-fare").textContent = fareRanges.taxi;
  document.querySelector("#fare-total").textContent = fareRanges.jeepney;
  document.querySelector("#fare-route-label").textContent =
    `${route.labels[0]} to ${route.labels[1]} · ${passengerType.options[passengerType.selectedIndex].text} passenger`;
  fareError.textContent = "";
  fareError.classList.remove("is-visible");
}

fareForm.addEventListener("submit", (event) => {
  event.preventDefault();
  calculateFare();
});

fareFrom.addEventListener("change", calculateFare);
fareTo.addEventListener("change", calculateFare);
passengerType.addEventListener("change", calculateFare);
