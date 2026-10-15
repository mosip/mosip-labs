package io.mosip.selfregistration.util;

import io.mosip.kernel.core.logger.spi.Logger;
import io.mosip.kernel.logger.logback.factory.Logfactory;

/**
 * Logger for SelfReg which provides implementation from kernel logback.
 *
 */
public final class SelfRegistrationLogger {


	/**
	 * Instantiates a new id repo logger.
	 */
	private SelfRegistrationLogger() {
	}

	/**
	 * Method to get the logger for the class provided.
	 *
	 * @param clazz the clazz
	 * @return the logger
	 */
	public static Logger getLogger(Class<?> clazz) {
		return Logfactory.getSlf4jLogger(clazz);
	}
}
