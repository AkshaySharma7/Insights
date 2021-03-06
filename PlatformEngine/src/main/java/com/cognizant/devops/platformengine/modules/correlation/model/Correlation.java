package com.cognizant.devops.platformengine.modules.correlation.model;

/**
 * @author Vishal Ganjare (vganjare)
 */
public class Correlation {
	private CorrelationNode source;
	private CorrelationNode destination;
	public CorrelationNode getSource() {
		return source;
	}
	public void setSource(CorrelationNode source) {
		this.source = source;
	}
	public CorrelationNode getDestination() {
		return destination;
	}
	public void setDestination(CorrelationNode destination) {
		this.destination = destination;
	}
}
