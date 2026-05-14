function layoutFan(container) {
    const items = Array.from(container.children);
    const count = items.length;

    if (count === 0) return;

    const maxAngle = 60; // total spread (degrees)
    const step = count > 1 ? maxAngle / (count - 1) : 0;

    items.forEach((li, i) => {
        const angle = -maxAngle / 2 + step * i;
        const offset = (i - (count - 1) / 2) * 30; // horizontal spacing

        li.style.transform = `
            translateX(${offset}px)
            rotate(${angle}deg)
        `;
        li.style.zIndex = i; // ensures proper overlap
	li.style.setProperty('--angle', angle);
    });
}

class FanHand extends HTMLElement {
	connectedCallback() {
		this.update = () => layoutFan(this.firstElementChild);

		this.observer = new MutationObserver(this.update);
		this.observer.observe(this.firstElementChild, { childList: true });

		this.update();
	}

	disconnectedCallback() {
		this.observer.disconnect();
	}
}

customElements.define('ga-hand-fan', FanHand);
